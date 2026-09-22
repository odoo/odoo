{
    "name": "Integration: MQTT Streams",
    "category": "Hidden/Tools",
    "summary": "The MQTT protocol for integration.stream: one session per stream, held by the stream worker",
    "description": """
Registers the ``mqtt`` stream protocol (MQTT 5 over paho, ``mqtt://`` and
``mqtts://``). A stream of this protocol subscribes to the topics of its
``subscriptions`` and publishes what its outbox holds; the stream worker that
leads the database keeps the session open.
""",
    "author": "AgroMarin",
    "license": "LGPL-3",
    "depends": [
        "integration",
    ],
    "external_dependencies": {
        "python": [
            "paho-mqtt",
        ],
    },
    "auto_install": True,
}
