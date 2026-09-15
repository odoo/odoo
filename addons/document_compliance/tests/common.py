from datetime import date, timedelta

from odoo.tests.common import TransactionCase


class ComplianceCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.admin = cls.env.ref("base.user_admin")
        cls.folder = cls.env["document.document"].create(
            {"name": "Compliance Test Folder", "type": "folder"}
        )

    def _publish(self):
        """Refresh the compliance report before reading it.

        It is a materialized view, so it shows the last refresh and not the
        current transaction. REFRESH runs inside this transaction and does see
        its uncommitted rows -- but only the ones already flushed, because
        refresh() deliberately does not flush for its callers.
        """
        self.env.flush_all()
        self.env["document.compliance.report"].refresh()
        self.env.invalidate_all()

    @classmethod
    def _type(cls, code, **vals):
        return cls.env["document.type"].create(
            {
                "name": f"Type {code}",
                "code": code,
                "company_id": cls.company.id,
                **vals,
            }
        )

    @classmethod
    def _doc(cls, doc_type=None, days=None, **vals):
        if days is not None:
            vals["date_expiration"] = date.today() + timedelta(days=days)
        return cls.env["document.document"].create(
            {
                "name": vals.pop("name", "Compliance Doc"),
                "folder_id": cls.folder.id,
                "document_type_id": doc_type.id if doc_type else False,
                **vals,
            }
        )

    def _activities(self, doc):
        return self.env["mail.activity"].search(
            [("res_model", "=", "document.document"), ("res_id", "=", doc.id)]
        )

    def _stored(self, doc):
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT expiration_state, compliance_state FROM document_document WHERE id = %s",
            (doc.id,),
        )
        return self.env.cr.fetchone()
