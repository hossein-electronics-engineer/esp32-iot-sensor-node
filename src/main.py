import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def simulate_sensor_signal(dt=0.1, t_end=60.0, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(0, t_end + dt, dt)

    baseline = 2.5 + 0.2 * np.sin(0.2 * t)
    noise = rng.normal(0.0, 0.15, size=t.shape)

    signal = baseline + noise

    # Inject a few events/spikes
    event_mask = ((t > 15) & (t < 17)) | ((t > 35) & (t < 36.5)) | ((t > 50) & (t < 52))
    signal[event_mask] += 0.8

    return t, signal


def moving_average(signal, window_size=5):
    filtered = np.convolve(signal, np.ones(window_size) / window_size, mode="same")
    return filtered


def detect_events(filtered_signal, threshold=2.95):
    events = filtered_signal > threshold
    return events


def build_payload(timestamp, raw_value, filtered_value, event_flag):
    payload = {
        "timestamp_s": float(timestamp),
        "raw_value": float(raw_value),
        "filtered_value": float(filtered_value),
        "event_flag": bool(event_flag)
    }
    return payload


def save_results(t, raw_signal, filtered_signal, events):
    os.makedirs("results", exist_ok=True)

    df = pd.DataFrame({
        "time_s": t,
        "raw_signal": raw_signal,
        "filtered_signal": filtered_signal,
        "event_flag": events.astype(int)
    })

    df.to_csv("results/sensor_stream.csv", index=False)
    return df


def plot_results(t, raw_signal, filtered_signal, events):
    os.makedirs("figures", exist_ok=True)

    plt.figure(figsize=(10, 4))
    plt.plot(t, raw_signal, label="Raw Signal", alpha=0.6)
    plt.plot(t, filtered_signal, label="Filtered Signal", linewidth=2)
    plt.xlabel("Time [s]")
    plt.ylabel("Sensor Value")
    plt.title("Raw vs Filtered Sensor Signal")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("figures/raw_vs_filtered_signal.png", dpi=200)
    plt.close()

    plt.figure(figsize=(10, 4))
    plt.plot(t, filtered_signal, label="Filtered Signal", linewidth=2)
    plt.plot(t[events], filtered_signal[events], "o", label="Detected Events")
    plt.xlabel("Time [s]")
    plt.ylabel("Sensor Value")
    plt.title("Event Detection")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("figures/event_detection.png", dpi=200)
    plt.close()


def save_sample_payloads(t, raw_signal, filtered_signal, events, num_samples=5):
    os.makedirs("results", exist_ok=True)

    payloads = []
    for i in range(min(num_samples, len(t))):
        payloads.append(
            build_payload(
                timestamp=t[i],
                raw_value=raw_signal[i],
                filtered_value=filtered_signal[i],
                event_flag=events[i]
            )
        )

    with open("results/sample_payloads.json", "w", encoding="utf-8") as f:
        json.dump(payloads, f, indent=2)


def main():
    os.makedirs("data", exist_ok=True)

    t, raw_signal = simulate_sensor_signal(dt=0.1, t_end=60.0, seed=42)
    filtered_signal = moving_average(raw_signal, window_size=7)
    events = detect_events(filtered_signal, threshold=2.95)

    save_results(t, raw_signal, filtered_signal, events)
    plot_results(t, raw_signal, filtered_signal, events)
    save_sample_payloads(t, raw_signal, filtered_signal, events, num_samples=10)

    print("IoT sensor node simulation completed successfully.")
    print("Results saved in: results/")
    print("Figures saved in: figures/")
    print("Generated files:")
    print("- results/sensor_stream.csv")
    print("- results/sample_payloads.json")
    print("- figures/raw_vs_filtered_signal.png")
    print("- figures/event_detection.png")


if __name__ == "__main__":
    main()
