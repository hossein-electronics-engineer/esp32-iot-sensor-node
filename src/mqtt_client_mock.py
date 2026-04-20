import json
from collections import defaultdict


class MockMQTTBroker:
    """
    In-memory mock MQTT broker for local testing.
    """

    def __init__(self):
        self.topics = defaultdict(list)

    def publish(self, topic: str, payload: dict):
        self.topics[topic].append(payload)

    def get_messages(self, topic: str):
        return self.topics.get(topic, [])

    def get_all_topics(self):
        return dict(self.topics)


class MockMQTTPublisher:
    """
    Mock publisher that sends packets to the mock broker.
    """

    def __init__(self, broker: MockMQTTBroker):
        self.broker = broker

    def publish(self, topic: str, payload: dict):
        self.broker.publish(topic, payload)

    @staticmethod
    def to_json(payload: dict) -> str:
        return json.dumps(payload)


class TelemetryTopicRouter:
    """
    Builds topic names in an MQTT/Azure-ready style.
    """

    def __init__(self, base_topic="iot/esp32"):
        self.base_topic = base_topic

    def telemetry_topic(self, node_id: str) -> str:
        return f"{self.base_topic}/{node_id}/telemetry"

    def heartbeat_topic(self, node_id: str) -> str:
        return f"{self.base_topic}/{node_id}/heartbeat"

    def event_topic(self, node_id: str) -> str:
        return f"{self.base_topic}/{node_id}/event"
