import base64
import json
import unittest
import zipfile
from io import BytesIO
from xml.etree import ElementTree as ET

from odoo.tests.common import TransactionCase


class TestGovXlsxWorker(TransactionCase):
    def setUp(self):
        super().setUp()
        try:
            import xlsxwriter  # noqa: F401
        except ImportError as exc:
            raise unittest.SkipTest("xlsxwriter nao instalado no ambiente de teste") from exc
        self.processo = self.env["gov.processo"].create(
            {
                "subject": "Aquisicao de materiais de limpeza",
            }
        )
        self.doc = self.env["gov.processo.doc"].create(
            {
                "processo_id": self.processo.id,
                "name": "DFD com planilha",
                "doc_type": "dfd",
            }
        )

    def _create_parameter(self, key, value_text, fase=0):
        parameter = self.env["gov.processo.parametro"].search(
            [
                ("processo_id", "=", self.processo.id),
                ("key", "=", key),
            ],
            limit=1,
        )
        values = {
            "processo_id": self.processo.id,
            "key": key,
            "name": key.replace("_", " ").title(),
            "fase": fase,
            "section": "additional_fields",
            "value_type": "json",
            "value_text": value_text,
        }
        if parameter:
            parameter.with_context(skip_phase_lock=True).write(values)
            return parameter
        return self.env["gov.processo.parametro"].create(values)

    def _get_sheet_formulas(self, workbook_binary, target):
        namespace = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        with zipfile.ZipFile(BytesIO(workbook_binary)) as zipped:
            root = ET.fromstring(zipped.read(target))
            formulas = []
            for cell in root.findall(".//m:c", namespace):
                formula = cell.find("m:f", namespace)
                if formula is not None and (formula.text or "").strip():
                    formulas.append(formula.text.strip())
            return formulas

    def test_worker_generates_xlsx_and_updates_document(self):
        self._create_parameter(
            "xlsx_item_rows_json",
            json.dumps(
                [
                    {
                        "lot_code": "1",
                        "item_number": "1",
                        "class_abc": "A",
                        "lot_description": "Alcoois e antissepticos",
                        "description": "Alcool 70%",
                        "unit": "Fr",
                        "monthly_quantity": 10,
                        "annual_quantity": 120,
                        "unit_price": 7.5,
                        "specification": "Registro ANVISA",
                    },
                    {
                        "lot_code": "1",
                        "item_number": "2",
                        "class_abc": "A",
                        "lot_description": "Alcoois e antissepticos",
                        "description": "Sabonete antisseptico",
                        "unit": "Fr",
                        "monthly_quantity": 4,
                        "annual_quantity": 48,
                        "unit_price": 18.5,
                        "specification": "Clorexidina 2%",
                    },
                    {
                        "lot_code": "2",
                        "item_number": "3",
                        "class_abc": "B",
                        "lot_description": "Residuos e desinfetantes",
                        "description": "Saco infectante",
                        "unit": "Rl",
                        "monthly_quantity": 3,
                        "annual_quantity": 36,
                        "unit_price": 95.0,
                        "specification": "Rolo 100 un.",
                    },
                ]
            ),
        )

        job = self.env["gov.processo.planilha.job"].create_from_doc(self.doc)
        job.action_process_now()

        self.assertEqual(job.state, "done")
        self.assertTrue(job.file_data)
        self.assertTrue(self.doc.pesquisa_precos_planilha)
        self.assertTrue(job.file_name.endswith(".xlsx"))

        workbook_binary = base64.b64decode(job.file_data)
        with zipfile.ZipFile(BytesIO(workbook_binary)) as zipped:
            names = set(zipped.namelist())
            self.assertIn("xl/workbook.xml", names)
            self.assertIn("xl/worksheets/sheet1.xml", names)
            self.assertIn("xl/worksheets/sheet2.xml", names)
            self.assertIn("xl/worksheets/sheet3.xml", names)

        item_formulas = self._get_sheet_formulas(workbook_binary, "xl/worksheets/sheet1.xml")
        lot_formulas = self._get_sheet_formulas(workbook_binary, "xl/worksheets/sheet2.xml")
        self.assertIn("F9*H9", item_formulas)
        self.assertTrue(any("SUM(J9:J10)" in formula for formula in item_formulas))
        self.assertTrue(any("COUNTIF" in formula for formula in lot_formulas))

    def test_worker_accepts_lot_only_payload_with_synthetic_items(self):
        self._create_parameter(
            "xlsx_lot_rows_json",
            json.dumps(
                [
                    {
                        "lot_code": "1",
                        "description": "Lote sintetico",
                        "class_abc": "C",
                        "expected_value": 1200.0,
                    }
                ]
            ),
            fase=1,
        )

        job = self.env["gov.processo.planilha.job"].create_from_doc(self.doc)
        job.action_process_now()

        self.assertEqual(job.state, "done")
        self.assertEqual(job.row_count, 1)
        self.assertEqual(job.lot_count, 1)
