import json

from odoo.tools import file_open


# Load file content once for all tests
with file_open('l10n_pl/tests/utils/fake_response.json') as file:
    file_content = json.load(file)


class FakeResponse:
    def __init__(self, endpoint):
        self.status_code, self.content = self._get_content(self._sanitize_endpoint(endpoint))

    def _sanitize_endpoint(self, endpoint):
        # We need to sort endpoints in asc order for testing
        parts = endpoint.split('/')
        nips = parts.pop(-1).split(',')
        nips.sort()
        return '/'.join(parts + [','.join(nips)])

    def _get_content(self, endpoint):
        data = file_content[endpoint]
        return data['status_code'], json.dumps(data['content']).encode()
