import json
import requests.exceptions

from odoo.tools import file_open

# Load file content once for all tests
with file_open('l10n_pl_bank_verification/tests/utils/fake_response.json') as file:
    file_content = json.load(file)


class FakeResponse:
    def __init__(self, combinations):
        self.status_code, self.content = self._get_content(combinations)

    def _get_content(self, combinations):
        data = []
        for vat, account in combinations:
            content = file_content[f'{vat}:{account}']
            if content['status_code'] != 200:
                return content['status_code'], json.dumps(content['content']).encode()
            data.append(content['content'])

        return 200, json.dumps(data).encode()

    def raise_for_status(self):
        if self.status_code != 200:
            raise requests.exceptions.RequestException()

    def json(self):
        return json.loads(self.content.decode())
