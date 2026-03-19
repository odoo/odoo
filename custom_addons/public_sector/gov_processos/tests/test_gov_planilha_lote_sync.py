import json

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestGovPlanilhaLoteSync(TransactionCase):
    def setUp(self):
        super().setUp()
        self.processo = self.env["gov.processo"].create(
            {
                "subject": "Processo com lotes estruturados",
            }
        )

    def test_sync_creates_lot_records_from_items(self):
        self.env["gov.processo.planilha.item"].create(
            {
                "processo_id": self.processo.id,
                "lot_code": "10",
                "item_number": 1,
                "class_abc": "A",
                "lot_description": "Saneantes",
                "description": "Alcool 70%",
                "unit": "Fr",
                "annual_quantity": 120,
                "unit_price": 7.5,
            }
        )

        lote = self.processo.planilha_lot_ids.filtered(lambda rec: rec.lot_code == "10")
        self.assertEqual(len(lote), 1)
        self.assertEqual(lote.description_effective, "Saneantes")
        self.assertEqual(lote.class_abc_effective, "A")
        self.assertEqual(lote.jan, "OF 30-45 d")
        self.assertEqual(lote.out, "OF 30-45 d")

    def test_lot_override_updates_structured_parameters(self):
        self.env["gov.processo.planilha.item"].create(
            {
                "processo_id": self.processo.id,
                "lot_code": "2",
                "item_number": 1,
                "class_abc": "B",
                "lot_description": "Desinfetantes",
                "description": "Desinfetante hospitalar",
                "unit": "Fr",
                "annual_quantity": 60,
                "unit_price": 10.0,
            }
        )
        self.processo.action_avancar_fase()
        lote = self.processo.planilha_lot_ids.filtered(lambda rec: rec.lot_code == "2")

        lote.write(
            {
                "description_override": "Lote 2 ajustado",
                "class_abc_override": "C",
                "notes": "Entrega fracionada",
                "jan": "Pedido piloto",
                "ago": "Reposicao sazonal",
            }
        )

        parameter_map = {parameter.key: parameter for parameter in self.processo.parameter_ids}
        lot_rows = json.loads(parameter_map["xlsx_lot_rows_json"].value_text)
        schedule_rows = json.loads(parameter_map["xlsx_schedule_rows_json"].value_text)

        self.assertEqual(lot_rows[0]["description"], "Lote 2 ajustado")
        self.assertEqual(lot_rows[0]["class_abc"], "C")
        self.assertEqual(lot_rows[0]["notes"], "Entrega fracionada")
        self.assertEqual(schedule_rows[0]["jan"], "Pedido piloto")
        self.assertEqual(schedule_rows[0]["ago"], "Reposicao sazonal")

    def test_closed_phase_lot_cannot_be_edited(self):
        self.env["gov.processo.planilha.item"].create(
            {
                "processo_id": self.processo.id,
                "lot_code": "7",
                "item_number": 1,
                "description": "Item base",
            }
        )
        self.processo.action_avancar_fase()
        lote = self.processo.planilha_lot_ids.filtered(lambda rec: rec.lot_code == "7")
        self.processo.action_avancar_fase()

        with self.assertRaises(ValidationError):
            lote.write({"notes": "Tentativa apos fechamento da fase"})
