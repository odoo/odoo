import base64

from odoo.tests.common import TransactionCase


class TestGovAuditoriaImportWizard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.fiscal_year = cls.env["account.fiscal.year"].create(
            {
                "name": "FY 2024 Import",
                "company_id": cls.company.id,
                "date_from": "2024-01-01",
                "date_to": "2024-12-31",
            }
        )
        cls.orgao = cls.env.ref("gov_auditoria.gov_auditoria_orgao_tce")

    def test_csv_import_creates_mirror_entries(self):
        ciclo = self.env["gov.auditoria.ciclo"].create(
            {
                "company_id": self.company.id,
                "exercicio_id": self.fiscal_year.id,
                "orgao_id": self.orgao.id,
                "tipo_prestacao": "ordinaria",
                "modo_dados": "espelho",
            }
        )
        csv_bytes = "tipo_movimento;data_movimento;valor;historico\nempenho;2024-02-10;100.50;Empenho reconstruido\n".encode("utf-8")
        wizard = self.env["gov.auditoria.espelho.import.wizard"].create(
            {
                "ciclo_id": ciclo.id,
                "upload_file": base64.b64encode(csv_bytes).decode("ascii"),
                "upload_filename": "espelho.csv",
            }
        )
        wizard.action_import()
        self.assertEqual(len(ciclo.espelho_ids), 1)
        self.assertEqual(ciclo.espelho_ids[0].origem, "importado_csv")
