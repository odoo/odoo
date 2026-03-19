import hashlib
from unittest.mock import patch

from odoo.tests.common import TransactionCase

from odoo.addons.gov_processos.services.gov_typst_serializer import GovTypstSerializer


class TestGovTypstStructuredRender(TransactionCase):
    def setUp(self):
        super().setUp()
        self.processo = self.env["gov.processo"].create(
            {
                "subject": "Aquisicao emergencial de insumos hospitalares",
            }
        )
        self.template = self.env["gov.ai.template"].create(
            {
                "name": "Template Typst Estruturado",
                "doc_type": "dfd",
                "process_type": "compras_servicos",
                "process_scope": "all",
                "fase": 0,
                "output_format": "typst",
                "typst_template": '#import "dados.typ": *\n\n= #documento.nome\n#par([#processo.numero])\n',
            }
        )
        self.doc = self.env["gov.processo.doc"].create(
            {
                "processo_id": self.processo.id,
                "name": "Justificativa Estruturada",
                "doc_type": "dfd",
                "ai_template_id": self.template.id,
                "template_ref": self.template.id,
                "render_mode": "structured_typst",
            }
        )

    def test_typst_serializer_emits_nested_bindings(self):
        serializer = GovTypstSerializer()
        serialized = serializer.dumps_all(
            {
                "ente": {"municipio": "Borba", "estado": "AM"},
                "ativo": True,
                "itens": ["a", "b"],
            }
        )

        self.assertIn("#let ente = (", serialized)
        self.assertIn('municipio: "Borba"', serialized)
        self.assertIn("#let ativo = true", serialized)
        self.assertIn("#let itens = (", serialized)

    def test_enqueue_structured_render_freezes_snapshots(self):
        job = self.env["gov.processo.doc.render.job"].create_from_doc(self.doc)

        self.assertEqual(job.state, "pending")
        self.assertEqual(job.doc_id, self.doc)
        self.assertEqual(self.doc.render_state, "queued")
        self.assertEqual(self.doc.last_render_job_id, job)
        self.assertIn("#let ente = (", job.dados_frozen)
        self.assertIn('#import "dados.typ": *', job.template_snapshot)

        frozen_template = job.template_snapshot
        self.template.write({"typst_template": '#import "dados.typ": *\n= "alterado"\n'})
        self.assertEqual(job.template_snapshot, frozen_template)

    def test_process_job_updates_document_and_pdf(self):
        job = self.env["gov.processo.doc.render.job"].create_from_doc(self.doc)
        pdf_bytes = b"%PDF-1.4 structured render test"
        expected_sha = hashlib.sha256(pdf_bytes).hexdigest()

        with patch(
            "odoo.addons.gov_processos.models.gov_processo_doc_render_job.GovTypstWorkspace.compile",
            return_value=pdf_bytes,
        ):
            job._process_job()

        job = self.env["gov.processo.doc.render.job"].browse(job.id)
        doc = self.env["gov.processo.doc"].browse(self.doc.id)

        self.assertEqual(job.state, "done")
        self.assertEqual(job.pdf_sha256, expected_sha)
        self.assertTrue(job.pdf_file)
        self.assertEqual(doc.render_state, "done")
        self.assertEqual(doc.hash_sha256, expected_sha)
        self.assertTrue(doc.pdf_file)
        self.assertTrue(doc.render_attachment_id)
