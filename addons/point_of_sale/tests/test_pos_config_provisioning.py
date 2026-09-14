import logging

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.common import TestPoSCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestPosConfigProvisioning(TestPoSCommon):
    def test_cash_reference_must_identify_an_active_cash_method(self):
        Config = self.env["pos.config"]
        archived = self.cash_pm1.copy({"active": False})
        for record in (self.bank_pm1, archived, self.env.company):
            with self.subTest(model=record._name, record=record.id):
                reference = Config._get_suffixed_ref_name(
                    "point_of_sale.provisioning_invalid_cash"
                )
                self.env["ir.model.data"]._update_xmlids(
                    [
                        {"xml_id": reference, "record": record, "noupdate": True},
                    ]
                )
                _logger.debug(
                    "Cash reference validation model=%s id=%s", record._name, record.id
                )
                with self.assertRaises(UserError):
                    Config._create_journal_and_payment_methods(
                        cash_ref="point_of_sale.provisioning_invalid_cash"
                    )

    def test_cash_creation_rejects_non_cash_journal(self):
        _logger.debug("Rejecting bank journal override in cash provisioning")
        with self.assertRaises(UserError):
            self.env["pos.config"]._create_cash_payment_method({"type": "bank"})

    def test_cash_creation_rejects_foreign_company_override(self):
        company = self.env["res.company"].create({"name": "Foreign cash override"})
        _logger.debug("Rejecting cash company override %s", company.id)
        with self.assertRaises(UserError):
            self.env["pos.config"]._create_cash_payment_method(
                {"company_id": company.id}
            )

    def test_provisioning_does_not_reuse_anonymous_customer_accounts(self):
        self.env["pos.payment.method"].search(
            [
                ("company_id", "=", self.env.company.id),
                ("journal_id", "=", False),
            ]
        ).write({"active": False})
        anonymous = self.env["pos.payment.method"].create(
            {
                "name": "Anonymous receivable",
                "company_id": self.env.company.id,
                "split_transactions": False,
            }
        )
        _journal, ids = self.env["pos.config"]._create_journal_and_payment_methods()
        methods = self.env["pos.payment.method"].browse(ids)
        _logger.debug(
            "Provisioned customer accounts=%s anonymous=%s",
            methods.filtered(lambda method: not method.journal_id).ids,
            anonymous.id,
        )
        self.assertNotIn(anonymous, methods)
        self.assertTrue(methods.filtered(lambda method: not method.journal_id))
        self.assertTrue(
            all(
                method.split_transactions for method in methods if not method.journal_id
            )
        )

    def test_provisioning_excludes_archived_methods_with_active_test_disabled(self):
        archived = self.bank_pm1.copy({"name": "Archived card", "active": False})
        _journal, ids = (
            self.env["pos.config"]
            .with_context(active_test=False)
            ._create_journal_and_payment_methods()
        )
        methods = self.env["pos.payment.method"].browse(ids)
        _logger.debug("Provisioned methods=%s archived=%s", ids, archived.id)
        self.assertNotIn(archived, methods)
        self.assertTrue(all(method.active for method in methods))
