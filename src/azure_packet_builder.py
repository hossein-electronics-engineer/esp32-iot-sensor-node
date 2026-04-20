import json
from datetime import datetime, timezone


class AzureReadyPacketBuilder:
    """
    Builds Azure-ready telemetry, heartbeat, and event packets
    for an IoT sensor node.
    """

    def __init__(
        self,
        device_id="esp32-node-01",
        device_type="esp32-sensor-node",
        firmware_version="1.0.0",
        location="lab"
    ):
        self.device_id = device_id
        self.device_type = device_type
        self.firmware_version = firmware_version
        self.location = location

    @staticmethod
    def utc_timestamp():
        return datetime.now(timezone.utc).isoformat()

    def base_metadata(self):
        return {
            "device_id": self.device_id,
            "device_type": self.device_type,
            "firmware_version": self.firmware_version,
            "location": self.location,
            "cloud_timestamp": self.utc_timestamp()
        }

    def build_telemetry_packet(
        self,
        sample_index,
        timestamp_s,
        raw_value,
        filtered_value,
        event_flag,
        signal_quality="nominal"
    ):
        packet = {
            **self.base_metadata(),
            "message_type": "telemetry",
            "sample_index": int(sample_index),
            "timestamp_s": float(timestamp_s),
            "sensor_data": {
                "raw_value": float(raw_value),
                "filtered_value": float(filtered_value),
                "signal_quality": signal_quality
            },
            "event_flag": bool(event_flag)
        }
        return packet

    def build_heartbeat_packet(
        self,
        sample_index,
        timestamp_s,
        last_filtered_value,
        last_event_flag,
        wifi_status="connected",
        mqtt_status="connected",
        cpu_load_pct=22.5,
        free_heap_kb=128.0
    ):
        packet = {
            **self.base_metadata(),
            "message_type": "heartbeat",
            "sample_index": int(sample_index),
            "timestamp_s": float(timestamp_s),
            "status": {
                "node_status": "alive",
                "wifi_status": wifi_status,
                "mqtt_status": mqtt_status,
                "cpu_load_pct": float(cpu_load_pct),
                "free_heap_kb": float(free_heap_kb)
            },
            "last_filtered_value": float(last_filtered_value),
            "last_event_flag": bool(last_event_flag)
        }
        return packet

    def build_event_packet(
        self,
        sample_index,
        timestamp_s,
        raw_value,
        filtered_value,
        severity="medium",
        event_type="threshold_crossing"
    ):
        packet = {
            **self.base_metadata(),
            "message_type": "event",
            "sample_index": int(sample_index),
            "timestamp_s": float(timestamp_s),
            "event": {
                "event_type": event_type,
                "severity": severity,
                "raw_value": float(raw_value),
                "filtered_value": float(filtered_value)
            }
        }
        return packet

    @staticmethod
    def to_json(packet: dict) -> str:
        return json.dumps(packet, indent=2)
