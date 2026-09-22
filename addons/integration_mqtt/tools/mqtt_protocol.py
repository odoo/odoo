import logging
import ssl
import threading
from urllib.parse import urlsplit

import paho.mqtt.client as mqtt

from odoo.addons.integration.tools.stream_protocol import StreamProtocol, register

_logger = logging.getLogger(__name__)

_DEFAULT_PORTS = {"mqtt": 1883, "mqtts": 8883}


class MqttHandle:
    __slots__ = ("client", "connected", "lock", "stream", "topics")

    def __init__(self, client, stream, topics):
        self.client = client
        self.stream = stream
        self.topics = topics
        self.connected = threading.Event()
        self.lock = threading.Lock()


@register
class MqttProtocol(StreamProtocol):
    """MQTT 5 over paho: the client's own network thread carries the session;
    frames are the messages of the subscribed topics, a send is a publish."""

    key = "mqtt"
    label = "MQTT"
    schemes = ("mqtt", "mqtts")

    def open(self, stream, on_frame, on_state):
        url = urlsplit(stream.url)
        options = stream.options
        client = mqtt.Client(  # noqa: E8518 - the broker's address was checked by ir.egress on the snapshot; paho holds the socket open
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=options.get("client_id") or f"odoo-stream-{stream.id}",
            protocol=mqtt.MQTTv5,
        )
        if stream.login or stream.secret:
            client.username_pw_set(stream.login or "", stream.secret or "")
        if url.scheme == "mqtts":
            context = ssl.create_default_context()
            if options.get("ca_certs"):
                context.load_verify_locations(options["ca_certs"])
            client.tls_set_context(context)
        topics = [
            (topic, int(options.get("qos", 1)))
            for topic in (stream.subscriptions or {}).get("topics", [])
            if topic
        ]
        handle = MqttHandle(client, stream, topics)

        def on_connect(client, userdata, flags, reason_code, properties):
            if reason_code == 0:
                for topic, qos in topics:
                    client.subscribe(topic, qos)
                handle.connected.set()
                on_state("open", None)
            else:
                on_state("error", f"connection refused: {reason_code}")

        def on_disconnect(client, userdata, flags, reason_code, properties):
            handle.connected.clear()
            if reason_code != 0:
                on_state("backoff", f"disconnected: {reason_code}")

        def on_message(client, userdata, message):
            on_frame(
                message.payload,
                {"topic": message.topic, "qos": message.qos, "retain": message.retain},
            )

        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message
        properties = mqtt.Properties(mqtt.PacketTypes.CONNECT)
        if options.get("session_expiry_interval"):
            properties.SessionExpiryInterval = int(options["session_expiry_interval"])
        # A pinned address for a plain session; a TLS session dials by name so
        # the certificate is checked against it.
        host = (
            stream.addresses[0]
            if stream.addresses and url.scheme == "mqtt"
            else url.hostname
        )
        client.connect(
            host,
            url.port or _DEFAULT_PORTS[url.scheme],
            keepalive=max(stream.heartbeat_seconds, 5),
            clean_start=mqtt.MQTT_CLEAN_START_FIRST_ONLY,
            properties=properties,
        )
        client.loop_start()
        return handle

    def send(self, handle, payload, meta):
        topic = meta.get("topic") or handle.stream.options.get("publish_topic")
        if not topic:
            raise ValueError("an MQTT frame names its topic")
        info = handle.client.publish(
            topic,
            payload,
            qos=int(meta.get("qos", handle.stream.options.get("qos", 1))),
            retain=bool(meta.get("retain", False)),
        )
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise OSError(f"publish refused: {mqtt.error_string(info.rc)}")
        info.wait_for_publish(timeout=10)

    def alive(self, handle):
        return handle.client.is_connected()

    def close(self, handle):
        with handle.lock:
            try:
                handle.client.disconnect()
            finally:
                handle.client.loop_stop()
