import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from esp32_node import ESP32SensorNode
from mqtt_client_mock import MockMQTTBroker, MockMQTTPublisher, TelemetryTopicRouter
from azure_packet_builder import AzureReadyPacketBuilder


def simulate_sensor_signal(dt=0.1, t_end=60.0, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(0, t_end + dt, dt)

    baseline = 2.5 + 0.2 * np.sin(0.2 * t)
    noise = rng.normal(0.0, 0.15, size=t.shape)

    signal = baseline + noise

    event_mask = ((t > 15) & (t < 17)) | ((t > 35) & (t < 36.5)) | ((t > 50) & (t < 52))
    signal[event_mask] += 0.8

    return t, signal


def estimate_signal_quality(filtered_value):
    if filtered_value > 3.3:
        return "high"
    elif filtered_value < 2.2:
        return "low"
    return "nominal"


def save_logs(telemetry_packets, heartbeat_packets, event_packets):
    os.makedirs("results", exist_ok=True)

    with open("results/azure_ready_telemetry_log.json", "w", encoding="utf-8") as f:
        json.dump(telemetry_packets, f, indent=2)

    with open("results/azure_ready_heartbeat_log.json", "w", encoding="utf-8") as f:
        json.dump(heartbeat_packets, f, indent=2)

    with open("results/azure_ready_event_log.json", "w", encoding="utf-8") as f:
        json.dump(event_packets, f, indent=2)


def save_summary(summary_df):
    os.makedirs("results", exist_ok=True)
    summary_df.to_csv("results/azure_ready_pipeline_summary.csv", index=False)


def save_sample_packets(sample_packets):
    os.makedirs("results", exist_ok=True)
    with open("results/azure_ready_sample_packets.json", "w", encoding="utf-8") as f:
        json.dump(sample_packets, f, indent=2)


def plot_summary(summary_df):
    os.makedirs("figures", exist_ok=True)

    plt.figure(figsize=(10, 4))
    plt.plot(summary_df["time_s"], summary_df["filtered_value"], label="Filtered Value", linewidth=2)
    plt.plot(
        summary_df.loc[summary_df["event_flag"] == 1, "time_s"],
        summary_df.loc[summary_df["event_flag"] == 1, "filtered_value"],
        "o",
        label="Azure-ready Event Packets"
    )
    plt.xlabel("Time [s]")
    plt.ylabel("Sensor Value")
    plt.title("Azure-ready Telemetry and Event Flow")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("figures/azure_ready_event_summary.png", dpi=200)
    plt.close()

    plt.figure(figsize=(10, 4))
    heartbeat_count = np.cumsum(summary_df["heartbeat_flag"].to_numpy())
    plt.plot(summary_df["time_s"], heartbeat_count, label="Cumulative Heartbeat Count", linewidth=2)
    plt.xlabel("Time [s]")
    plt.ylabel("Count")
    plt.title("Azure-ready Heartbeat Activity")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("figures/azure_ready_heartbeat_summary.png", dpi=200)
    plt.close()


def main():
    os.makedirs("data", exist_ok=True)
    os.makedirs("results", exist_ok=True)
    os.makedirs("figures", exist_ok=True)

    t, raw_signal = simulate_sensor_signal(dt=0.1, t_end=60.0, seed=42)

    node = ESP32SensorNode(
        node_id="esp32-node-01",
        filter_window=7,
        event_threshold=2.95,
        heartbeat_interval_samples=20
    )

    broker = MockMQTTBroker()
    publisher = MockMQTTPublisher(broker)
    router = TelemetryTopicRouter(base_topic="iot/esp32")

    azure_builder = AzureReadyPacketBuilder(
        device_id="esp32-node-01",
        device_type="esp32-sensor-node",
        firmware_version="1.0.0",
        location="lab"
    )

    summary_rows = []

    for timestamp_s, raw_value in zip(t, raw_signal):
        out = node.step(timestamp_s=float(timestamp_s), raw_value=float(raw_value))

        filtered_value = out["filtered_value"]
        event_flag = out["event_flag"]

        signal_quality = estimate_signal_quality(filtered_value)

        telemetry_packet = azure_builder.build_telemetry_packet(
            sample_index=node.sample_index,
            timestamp_s=timestamp_s,
            raw_value=raw_value,
            filtered_value=filtered_value,
            event_flag=event_flag,
            signal_quality=signal_quality
        )

        publisher.publish(router.telemetry_topic(node.node_id), telemetry_packet)

        heartbeat_sent = 0
        if out["heartbeat_packet"] is not None:
            heartbeat_packet = azure_builder.build_heartbeat_packet(
                sample_index=node.sample_index,
                timestamp_s=timestamp_s,
                last_filtered_value=filtered_value,
                last_event_flag=event_flag,
                wifi_status="connected",
                mqtt_status="connected",
                cpu_load_pct=22.5,
                free_heap_kb=128.0
            )
            publisher.publish(router.heartbeat_topic(node.node_id), heartbeat_packet)
            heartbeat_sent = 1

        if event_flag:
            event_packet = azure_builder.build_event_packet(
                sample_index=node.sample_index,
                timestamp_s=timestamp_s,
                raw_value=raw_value,
                filtered_value=filtered_value,
                severity="medium",
                event_type="threshold_crossing"
            )
            publisher.publish(router.event_topic(node.node_id), event_packet)

        summary_rows.append({
            "time_s": timestamp_s,
            "raw_value": raw_value,
            "filtered_value": filtered_value,
            "event_flag": int(event_flag),
            "heartbeat_flag": heartbeat_sent
        })

    summary_df = pd.DataFrame(summary_rows)

    telemetry_packets = broker.get_messages(router.telemetry_topic(node.node_id))
    heartbeat_packets = broker.get_messages(router.heartbeat_topic(node.node_id))
    event_packets = broker.get_messages(router.event_topic(node.node_id))

    sample_packets = {
        "telemetry_example": telemetry_packets[0] if telemetry_packets else {},
        "heartbeat_example": heartbeat_packets[0] if heartbeat_packets else {},
        "event_example": event_packets[0] if event_packets else {}
    }

    save_logs(telemetry_packets, heartbeat_packets, event_packets)
    save_summary(summary_df)
    save_sample_packets(sample_packets)
    plot_summary(summary_df)

    print("Azure-ready IoT pipeline simulation completed successfully.")
    print(f"Telemetry packets published: {len(telemetry_packets)}")
    print(f"Heartbeat packets published: {len(heartbeat_packets)}")
    print(f"Event packets published: {len(event_packets)}")
    print("\nResults saved in: results/")
    print("Figures saved in: figures/")
    print("Generated files:")
    print("- results/azure_ready_telemetry_log.json")
    print("- results/azure_ready_heartbeat_log.json")
    print("- results/azure_ready_event_log.json")
    print("- results/azure_ready_pipeline_summary.csv")
    print("- results/azure_ready_sample_packets.json")
    print("- figures/azure_ready_event_summary.png")
    print("- figures/azure_ready_heartbeat_summary.png")


if __name__ == "__main__":
    main()
