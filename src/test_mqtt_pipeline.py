import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from esp32_node import ESP32SensorNode
from mqtt_client_mock import MockMQTTBroker, MockMQTTPublisher, TelemetryTopicRouter


def simulate_sensor_signal(dt=0.1, t_end=60.0, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(0, t_end + dt, dt)

    baseline = 2.5 + 0.2 * np.sin(0.2 * t)
    noise = rng.normal(0.0, 0.15, size=t.shape)

    signal = baseline + noise

    event_mask = ((t > 15) & (t < 17)) | ((t > 35) & (t < 36.5)) | ((t > 50) & (t < 52))
    signal[event_mask] += 0.8

    return t, signal


def save_pipeline_logs(telemetry_packets, heartbeat_packets, event_packets):
    os.makedirs("results", exist_ok=True)

    with open("results/mqtt_telemetry_log.json", "w", encoding="utf-8") as f:
        json.dump(telemetry_packets, f, indent=2)

    with open("results/mqtt_heartbeat_log.json", "w", encoding="utf-8") as f:
        json.dump(heartbeat_packets, f, indent=2)

    with open("results/mqtt_event_log.json", "w", encoding="utf-8") as f:
        json.dump(event_packets, f, indent=2)


def save_pipeline_summary(summary_df):
    os.makedirs("results", exist_ok=True)
    summary_df.to_csv("results/mqtt_pipeline_summary.csv", index=False)


def plot_pipeline_summary(summary_df):
    os.makedirs("figures", exist_ok=True)

    plt.figure(figsize=(10, 4))
    plt.plot(summary_df["time_s"], summary_df["filtered_value"], label="Filtered Value", linewidth=2)
    plt.plot(
        summary_df.loc[summary_df["event_flag"] == 1, "time_s"],
        summary_df.loc[summary_df["event_flag"] == 1, "filtered_value"],
        "o",
        label="Published Event Packets"
    )
    plt.xlabel("Time [s]")
    plt.ylabel("Sensor Value")
    plt.title("MQTT-ready Pipeline: Telemetry and Event Packets")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("figures/mqtt_pipeline_event_summary.png", dpi=200)
    plt.close()

    plt.figure(figsize=(10, 4))
    heartbeat_count = np.cumsum(summary_df["heartbeat_flag"].to_numpy())
    plt.plot(summary_df["time_s"], heartbeat_count, label="Cumulative Heartbeat Count", linewidth=2)
    plt.xlabel("Time [s]")
    plt.ylabel("Count")
    plt.title("MQTT-ready Pipeline: Heartbeat Activity")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("figures/mqtt_pipeline_heartbeat_summary.png", dpi=200)
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

    summary_rows = []

    for timestamp_s, raw_value in zip(t, raw_signal):
        out = node.step(timestamp_s=float(timestamp_s), raw_value=float(raw_value))

        telemetry_packet = out["telemetry_packet"]
        heartbeat_packet = out["heartbeat_packet"]
        event_flag = out["event_flag"]

        publisher.publish(router.telemetry_topic(node.node_id), telemetry_packet)

        heartbeat_sent = 0
        if heartbeat_packet is not None:
            publisher.publish(router.heartbeat_topic(node.node_id), heartbeat_packet)
            heartbeat_sent = 1

        if event_flag:
            publisher.publish(router.event_topic(node.node_id), telemetry_packet)

        summary_rows.append({
            "time_s": timestamp_s,
            "raw_value": raw_value,
            "filtered_value": out["filtered_value"],
            "event_flag": int(event_flag),
            "heartbeat_flag": heartbeat_sent
        })

    summary_df = pd.DataFrame(summary_rows)

    telemetry_packets = broker.get_messages(router.telemetry_topic(node.node_id))
    heartbeat_packets = broker.get_messages(router.heartbeat_topic(node.node_id))
    event_packets = broker.get_messages(router.event_topic(node.node_id))

    save_pipeline_logs(telemetry_packets, heartbeat_packets, event_packets)
    save_pipeline_summary(summary_df)
    plot_pipeline_summary(summary_df)

    print("MQTT-ready IoT pipeline simulation completed successfully.")
    print(f"Telemetry packets published: {len(telemetry_packets)}")
    print(f"Heartbeat packets published: {len(heartbeat_packets)}")
    print(f"Event packets published: {len(event_packets)}")
    print("\nResults saved in: results/")
    print("Figures saved in: figures/")
    print("Generated files:")
    print("- results/mqtt_telemetry_log.json")
    print("- results/mqtt_heartbeat_log.json")
    print("- results/mqtt_event_log.json")
    print("- results/mqtt_pipeline_summary.csv")
    print("- figures/mqtt_pipeline_event_summary.png")
    print("- figures/mqtt_pipeline_heartbeat_summary.png")


if __name__ == "__main__":
    main()
