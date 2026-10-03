from base64 import b64decode
from odoo import fields
from lxml import etree
from .common import PdpTestCommon


class TestPdpB2CSummaries(PdpTestCommon):
    def test_summary_vat_breakdown_present(self):
        """B2C summary must include VAT breakdown and amounts."""
        day = fields.Date.from_string("2025-02-01")
        self._create_invoice(date_val=day, sent=True)
        flows = self._run_aggregation()
        flow = flows.filtered(lambda f: f.report_kind == "transaction")
        payload_b64 = flow.slice_ids[0].payload
        xml = etree.fromstring(b64decode(payload_b64))
        summary = xml.find(".//TransactionsReport/Transactions")
        self.assertIsNotNone(summary, "Transactions summary block missing")
        vat_lines = summary.findall("./TaxSubtotal")
        self.assertTrue(vat_lines, "VAT breakdown missing in summary")
        # Amount fields must be present
        for node in vat_lines:
            taxable = node.find("TaxableAmount")
            tax = node.find("TaxTotal")
            self.assertIsNotNone(taxable, "TaxableAmount missing in VAT bucket")
            self.assertIsNotNone(tax, "TaxTotal missing in VAT bucket")
