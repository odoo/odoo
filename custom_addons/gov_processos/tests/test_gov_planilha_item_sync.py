import json

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestGovPlanilhaItemSync(TransactionCase):
    def setUp(self):
        super().setUp()
        self.processo = self.env["gov.processo"].create(
            {
                "subject": "Processo com itens estruturados",
            }
        )

    def test_planilha_item_syncs_structured_parameters(self):
        item = self.env["gov.processo.planilha.item"].create(
            {
                "processo_id": self.processo.id,
                "lot_code": "1",
                "item_number": 1,
                "class_abc": "A",
                "lot_description": "Grupo critico",
                "description": "Alcool 70%",
                "unit": "Fr",
                "monthly_quantity": 10,
                "annual_quantity": 120,
                "unit_price": 7.5,
                "specification": "Registro ANVISA",
            }
        )

        parameter_map = {parameter.key: parameter for parameter in self.processo.parameter_ids}
        self.assertIn("xlsx_item_rows_json", parameter_map)
        self.assertIn("xlsx_lot_rows_json", parameter_map)
        self.assertIn("xlsx_schedule_rows_json", parameter_map)

        item_rows = json.loads(parameter_map["xlsx_item_rows_json"].value_text)
        lot_rows = json.loads(parameter_map["xlsx_lot_rows_json"].value_text)
        schedule_rows = json.loads(parameter_map["xlsx_schedule_rows_json"].value_text)

        self.assertEqual(item_rows[0]["description"], "Alcool 70%")
        self.assertEqual(item_rows[0]["annual_quantity"], 120)
        self.assertEqual(lot_rows[0]["lot_code"], "1")
        self.assertEqual(lot_rows[0]["expected_value"], item.annual_total)
        self.assertEqual(schedule_rows[0]["jan"], "OF 30-45 d")

    def test_worker_payload_reads_structured_grid(self):
        self.env["gov.processo.planilha.item"].create(
            {
                "processo_id": self.processo.id,
                "lot_code": "2",
                "item_number": 4,
                "class_abc": "B",
                "lot_description": "Desinfetantes",
                "description": "Desinfetante quaternario",
                "unit": "Fr",
                "monthly_quantity": 5,
                "unit_price": 28.0,
            }
        )

        payload = self.env["gov.xlsx.worker.service"].build_procurement_payload(self.processo)

        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["annual_quantity"], 60.0)
        self.assertEqual(payload["lots"][0]["lot_code"], "2")
        self.assertEqual(payload["schedule"][0]["jan"], "OF 30-45 d")
        self.assertEqual(payload["schedule"][0]["dez"], "OF 30 d")

    def test_closed_phase_item_cannot_be_edited(self):
        item = self.env["gov.processo.planilha.item"].create(
            {
                "processo_id": self.processo.id,
                "lot_code": "1",
                "item_number": 1,
                "description": "Item inicial",
            }
        )
        self.processo.action_avancar_fase()

        with self.assertRaises(ValidationError):
            item.write({"description": "Tentativa tardia"})
