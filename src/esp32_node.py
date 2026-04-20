import json
from collections import deque


class ESP32SensorNode:
    """
    Firmware-style IoT sensor node simulation.

    Features:
    - sample-by-sample processing
    - moving average filtering
    - threshold-based event detection
    - telemetry packet generation
    - heartbeat/status packet generation
    """

    def __init__(
        self,
        node_id="esp32-node-01",
        filter_window=7,
        event_threshold=2.95,
        heartbeat_interval_samples=20
    ):
        self.node_id = node_id
        self.filter_window = filter_window
        self.event_threshold = event_threshold
        self.heartbeat_interval_samples = heartbeat_interval_samples

        self.sample_buffer = deque(maxlen=filter_window)
        self.sample_index = 0
        self.last_filtered_value = 0.0
        self.last_event_flag = False

    def apply_filter(self, raw_value: float) -> float:
        self.sample_buffer.append(raw_value)
        filtered_value = sum(self.sample_buffer) / len(self.sample_buffer)
        self.last_filtered_value = filtered_value
        return filtered_value

    def detect_event(self, filtered_value: float) -> bool:
        event_flag = filtered_value > self.event_threshold
        self.last_event_flag = event_flag
        return event_flag

    def build_telemetry_packet(self, timestamp_s: float, raw_value: float, filtered_value: float, event_flag: bool):
        packet = {
            "packet_type": "telemetry",
            "node_id": self.node_id,
            "sample_index": self.sample_index,
            "timestamp_s": float(timestamp_s),
            "raw_value": float(raw_value),
            "filtered_value": float(filtered_value),
            "event_flag": bool(event_flag)
        }
        return packet

    def build_heartbeat_packet(self, timestamp_s: float):
        packet = {
            "packet_type": "heartbeat",
            "node_id": self.node_id,
            "sample_index": self.sample_index,
            "timestamp_s": float(timestamp_s),
            "status": "alive",
            "last_filtered_value": float(self.last_filtered_value),
            "last_event_flag": bool(self.last_event_flag)
        }
        return packet

    def should_send_heartbeat(self) -> bool:
        if self.sample_index == 0:
            return True
        return self.sample_index % self.heartbeat_interval_samples == 0

    def step(self, timestamp_s: float, raw_value: float):
        filtered_value = self.apply_filter(raw_value)
        event_flag = self.detect_event(filtered_value)

        telemetry_packet = self.build_telemetry_packet(
            timestamp_s=timestamp_s,
            raw_value=raw_value,
            filtered_value=filtered_value,
            event_flag=event_flag
        )

        heartbeat_packet = None
        if self.should_send_heartbeat():
            heartbeat_packet = self.build_heartbeat_packet(timestamp_s=timestamp_s)

        self.sample_index += 1

        return {
            "filtered_value": filtered_value,
            "event_flag": event_flag,
            "telemetry_packet": telemetry_packet,
            "heartbeat_packet": heartbeat_packet
        }

    @staticmethod
    def packet_to_json(packet: dict) -> str:
        return json.dumps(packet)
