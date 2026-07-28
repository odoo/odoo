import typing
from collections import deque


class Plugin:
    """Base plugin"""

    def ingress(self, envelope, http_headers, operation):
        """Override to update the envelope or http headers when receiving a
        message.

        :param envelope: The envelope as XML node
        :param http_headers: Dict with the HTTP headers

        """
        return envelope, http_headers

    def egress(self, envelope, http_headers, operation, binding_options):
        """Override to update the envelope or http headers when sending a
        message.

        :param envelope: The envelope as XML node
        :param http_headers: Dict with the HTTP headers
        :param operation: The associated Operation instance
        :param binding_options: Binding specific options for the operation

        """
        return envelope, http_headers


def apply_egress(client, envelope, http_headers, operation, binding_options):
    for plugin in client.plugins:
        result = plugin.egress(envelope, http_headers, operation, binding_options)
        if result is not None:
            envelope, http_headers = result

    return envelope, http_headers


def apply_ingress(client, envelope, http_headers, operation):
    for plugin in client.plugins:
        result = plugin.ingress(envelope, http_headers, operation)
        if result is not None:
            envelope, http_headers = result

    return envelope, http_headers


class HistoryPlugin(Plugin):
    def __init__(self, maxlen=1):
        self._buffer = deque([], maxlen)

    @property
    def last_sent(self):
        last_tx = self._buffer[-1]
        if last_tx:
            return last_tx["sent"]

    @property
    def last_received(self) -> typing.Optional[typing.Dict[str, typing.Any]]:
        last_tx = self._buffer[-1]
        if last_tx:
            return last_tx["received"]
        return None

    def ingress(self, envelope, http_headers, operation):
        last_tx = self._buffer[-1]
        last_tx["received"] = {"envelope": envelope, "http_headers": http_headers}

    def egress(self, envelope, http_headers, operation, binding_options):
        self._buffer.append(
            {
                "received": None,
                "sent": {"envelope": envelope, "http_headers": http_headers},
            }
        )
