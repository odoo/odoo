{
    "name": "Integration: Modbus Streams",
    "category": "Hidden/Tools",
    "summary": "The Modbus protocol for integration.stream: a held link whose registers are read on the stream's heartbeat",
    "description": """
Registers the ``modbus`` stream protocol (``modbus://host:port`` for TCP,
``modbus+rtu:///dev/ttyUSB0?baudrate=9600`` for a serial line, on pymodbus).
A Modbus device pushes nothing: the stream's ``subscriptions`` name the
registers, the protocol reads them every ``heartbeat_seconds`` on a thread of
its own and hands each reading to the worker as a frame; a queued frame writes
registers or coils.
""",
    "author": "AgroMarin",
    "license": "LGPL-3",
    "depends": [
        "integration",
    ],
    "external_dependencies": {
        "python": [
            "pymodbus",
        ],
    },
    "auto_install": True,
}
