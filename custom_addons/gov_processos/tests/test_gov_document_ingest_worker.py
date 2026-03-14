import base64

from odoo.tests.common import TransactionCase


class TestGovDocumentIngestWorker(TransactionCase):
    def setUp(self):
        super().setUp()
        self.processo = self.env["gov.processo"].create(
            {
                "subject": "Processo com ingestão documental",
            }
        )

    def test_worker_converts_typst_upload_and_versions_document(self):
        doc = self.env["gov.processo.doc"].create(
            {
                "processo_id": self.processo.id,
                "name": "Nota Técnica",
                "doc_type": "despacho",
                "upload_externo": base64.b64encode(
                    b"= Nota Tecnica\n\nProcesso: {{processo_numero}}\n"
                ).decode("ascii"),
                "upload_externo_filename": "nota.typ",
                "ingest_target_format": "typst",
            }
        )

        job = self.env["gov.processo.doc.ingest.job"].create_from_doc(doc, target_format="typst")
        job.action_process_now()

        self.assertEqual(job.state, "done")
        self.assertEqual(job.source_input_format, "typst")
        self.assertIn("Processo:", doc.typst_source or "")
        self.assertTrue(doc.latex_source)
        self.assertTrue(doc.content_html)
        self.assertEqual(job.applied_version_number, doc.version)
        self.assertTrue(doc.versao_ids.filtered(lambda rec: rec.version_number == doc.version))

    def test_worker_converts_csv_upload_to_latex(self):
        doc = self.env["gov.processo.doc"].create(
            {
                "processo_id": self.processo.id,
                "name": "Tabela de Itens",
                "doc_type": "dfd",
                "upload_externo": base64.b64encode(
                    b"item,descricao,valor\n1,Detergente,25.00\n"
                ).decode("ascii"),
                "upload_externo_filename": "itens.csv",
                "ingest_target_format": "latex",
            }
        )

        job = self.env["gov.processo.doc.ingest.job"].create_from_doc(doc, target_format="latex")
        job.action_process_now()

        self.assertEqual(job.state, "done")
        self.assertEqual(job.source_input_format, "csv")
        self.assertIn("longtable", doc.latex_source or "")
        self.assertIn("Detergente", doc.latex_source or "")
        self.assertTrue(job.normalized_source)
