import json


from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon
from odoo.addons.l10n_in_reports.tests.common import L10nInTestAccountReportsCommon
from odoo.tools import file_open


class L10nInTestAccountGstReportsCommon(L10nInTestAccountReportsCommon, L10nInTestInvoicingCommon):

    @classmethod
    def _read_mock_json(self, filename):
        """
        Reads a JSON file using Odoo's file_open and returns the parsed data.

        :param filename: The name of the JSON file to read.
        :return: Parsed JSON data.
        """
        # Use file_open to open the file from the module's directory
        with file_open(f"{self.test_module}/tests/mock_jsons/{filename}", 'rb') as file:
            data = json.load(file)

        return data
