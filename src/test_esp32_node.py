import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from esp32_node import ESP32SensorNode


def simulate_sensor_signal(dt=0.1, t_end=60.0, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(0, t_end + dt, dt)

    baseline = 2.5 + 0.2 * np.sin(0.2 * t)
    noise = rng.normal(0.0, 0.15, size=t.shape)

    signal = baseline + noise

    event_mask = ((t > 15) & (t < 17)) | ((t > 35) & (t < 36.5)) | ((t > 50) & (t < 52))
    signal[event_mask] += 0.8

    return t, signal


def save_processed_stream(t, raw_signal, filtered_signal, event_flags):
    os.makedirs("results", exist_ok=True)

    df = pd.DataFrame({
        "time_s": t,
        "raw_signal": raw_signal,
        "filtered_signal": filtered_signal,
        "event_flag": np.array(event_flags, dtype=int)
    })
    df.to_csv("results/esp32_node_stream.csv", index=False)


def save_packets(telemetry_packets, heartbeat_packets):
    os.makedirs("results", exist_ok=True)

    with open("results/telemetry_packets.json", "w", encoding="utf-8") as f:
        json.dump(telemetry_packets, f, indent=2)

    with open("results/heartbeat_packets.json", "w", encoding="utf-8") as f:
        json.dump(heartbeat_packets, f, indent=2)


def plot_results(t, raw_signal, filtered_signal, event_flags):
    os.makedirs("figures", exist_ok=True)

    event_flags = np.array(event_flags, dtype=bool)

    plt.figure(figsize=(10, 4))
    plt.plot(t, raw_signal, label="Raw Signal", alpha=0.6)
    plt.plot(t, filtered_signal, label="Firmware-style Filtered Signal", linewidth=2)
    plt.xlabel("Time [s]")
    plt.ylabel("Sensor Value")
    plt.title("ESP32-style Node: Raw vs Filtered Signal")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("figures/esp32_node_filtered_signal.png", dpi=200)
    plt.close()

    plt.figure(figsize=(10, 4))
    plt.plot(t, filtered_signal, label="Filtered Signal", linewidth=2)
    plt.plot(t[event_flags], np.array(filtered_signal)[event_flags], "o", label="Detected Events")
    plt.xlabel("Time [s]")
    plt.ylabel("Sensor Value")
    plt.title("ESP32-style Node: Event Detection")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("figures/esp32_node_event_detection.png", dpi=200)
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

    filtered_signal = []
    event_flags = []
    telemetry_packets = []
    heartbeat_packets = []

    for timestamp_s, raw_value in zip(t, raw_signal):
        out = node.step(timestamp_s=float(timestamp_s), raw_value=float(raw_value))

        filtered_signal.append(out["filtered_value"])
        event_flags.append(out["event_flag"])
        telemetry_packets.append(out["telemetry_packet"])

        if out["heartbeat_packet"] is not None:
            heartbeat_packets.append(out["heartbeat_packet"])

    save_processed_stream(t, raw_signal, filtered_signal, event_flags)
    save_packets(telemetry_packets, heartbeat_packets)
    plot_results(t, raw_signal, filtered_signal, event_flags)

    print("ESP32-style IoT node simulation completed successfully.")
    print(f"Telemetry packets generated: {len(telemetry_packets)}")
    print(f"Heartbeat packets generated: {len(heartbeat_packets)}")
    print("\nResults saved in: results/")
    print("Figures saved in: figures/")
    print("Generated files:")
    print("- results/esp32_node_stream.csv")
    print("- results/telemetry_packets.json")
    print("- results/heartbeat_packets.json")
    print("- figures/esp32_node_filtered_signal.png")
    print("- figures/esp32_node_event_detection.png")


if __name__ == "__main__":
    main()
