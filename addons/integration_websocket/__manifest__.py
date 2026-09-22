{
    "name": "Integration: WebSocket Streams",
    "category": "Hidden/Tools",
    "summary": "The websocket protocol for integration.stream: one connection per stream, held by the stream worker",
    "description": """
Registers the ``websocket`` stream protocol (``ws://`` and ``wss://``, on
websocket-client). A stream of this protocol receives every text or binary
message as a frame and sends what its outbox holds; the stream worker that
leads the database keeps the connection open and pings it.
""",
    "author": "AgroMarin",
    "license": "LGPL-3",
    "depends": [
        "integration",
    ],
    "external_dependencies": {
        "python": [
            "websocket",
        ],
    },
    "auto_install": True,
}
