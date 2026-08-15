"""Invoice Agent queue topology package.

``topology.py`` declares the RabbitMQ 0-9-1 topology the invoice agent uses:
the durable ``invoice.agent`` topic exchange, the ``invoice.extract`` and
``invoice.result`` queues, and their bindings on ``extract.request`` /
``extract.done`` routing keys.

Run against the local broker with ``python -m invoice_queue.topology`` or with a
plain ``python invoice_queue/topology.py`` — both work because the module reads the
broker connection from the same environment variables ``docker-compose``
injects (``RABBITMQ_USER`` / ``RABBITMQ_PASS`` / ``RABBITMQ_HOST``).
"""
