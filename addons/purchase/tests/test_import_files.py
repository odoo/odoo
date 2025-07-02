import unittest

from odoo.tests import TransactionCase, can_import, loaded_demo_data, tagged
from odoo.tools.misc import file_open


@tagged("post_install", "-at_install")
class TestImportFiles(TransactionCase):

    @unittest.skipUnless(
        can_import("xlrd.xlsx") or can_import("openpyxl"), "XLRD/XLSX not available",
    )
    def test_import_requests_for_quotation_template_xls(self):
        if not loaded_demo_data(self.env):
            self.skipTest('Needs demo data to be able to import those files')
        model = "purchase.order"
        filename = "requests_for_quotation_import_template.xlsx"

        file_content = file_open(f"purchase/static/xls/{filename}", "rb").read()
        import_wizard = self.env["base_import.import"].create(
            {
                "res_model": model,
                "file": file_content,
                "file_type": "application/vnd.ms-excel",
            },
        )

        result = import_wizard.parse_preview(
            {
                "has_headers": True,
            },
        )
        self.assertIsNone(result.get("error"))
        field_names = ['/'.join(v) for v in result["matches"].values()]
        results = import_wizard.execute_import(
            field_names,
            [r.lower() for r in result["headers"]],
            {
                "import_skip_records": [],
                "import_set_empty_fields": [],
                "fallback_values": {},
                "name_create_enabled_fields": {},
                "encoding": "",
                "separator": "",
                "quoting": '"',
                "date_format": "",
                "datetime_format": "",
                "float_thousand_separator": ",",
                "float_decimal_separator": ".",
                "advanced": True,
                "has_headers": True,
                "keep_matches": False,
                "limit": 2000,
                "skip": 0,
                "tracking_disable": True,
            },
        )
        self.assertFalse(
            results["messages"],
            "results should be empty on successful import of ",
        )
