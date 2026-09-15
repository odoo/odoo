import logging
import time
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools.misc import file_open, formatLang

_logger = logging.getLogger(__name__)

_debug = DebugLog(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _prepare_demo_data(self, company=False):
        _debug.pipeline("demo_get_demo_data", company=company)
        return {
            **self._prepare_demo_data_products(company),
            "account.move": self._prepare_demo_data_move(company),
            "account.bank.statement": self._prepare_demo_data_statement(company),
            "account.bank.statement.line": self._prepare_demo_data_transactions(
                company
            ),
            "account.reconcile.model": self._prepare_demo_data_reconcile_model(company),
            "ir.attachment": self._prepare_demo_data_attachment(company),
            "mail.message": self._prepare_demo_data_mail_message(company),
            "mail.activity": self._prepare_demo_data_mail_activity(company),
            "product.product": self._prepare_demo_data_product(),
            "res.partner.bank": self._prepare_demo_data_bank(company),
            "res.partner": self._prepare_demo_data_partner(),
            "res.users": self._prepare_demo_data_user(),
            "account.journal": self._prepare_demo_data_journal(company),
        }

    def _get_demo_exception_product_template_xml_ids(self):
        return []

    def _get_demo_exception_product_variant_xml_ids(self):
        return ["product.office_combo"]

    @_debug.perf.timed
    def _prepare_demo_data_products(self, company):
        if company != self.env.ref("base.main_company", raise_if_not_found=False):
            return {}

        taxes = {}
        if company.account_sale_tax_id:
            taxes.update({"taxes_id": [Command.link(company.account_sale_tax_id.id)]})
        if company.account_purchase_tax_id:
            taxes.update(
                {
                    "supplier_taxes_id": [
                        Command.link(company.account_purchase_tax_id.id)
                    ]
                }
            )
        _debug.logic(
            "demo_product_taxes_resolved",
            company=company,
            tax_fields=len(taxes),
            skipped=not taxes,
        )
        if not taxes:
            return {}
        IMD = self.env["ir.model.data"].sudo()
        product_templates = sorted(
            set(
                IMD.search([("model", "=", "product.template")]).mapped("complete_name")
            )
            - set(self._get_demo_exception_product_template_xml_ids())
        )
        product_variants = sorted(
            set(IMD.search([("model", "=", "product.product")]).mapped("complete_name"))
            - set(self._get_demo_exception_product_variant_xml_ids())
        )
        _debug.pipeline(
            "demo_products_taxed",
            company=company,
            templates=len(product_templates),
            variants=len(product_variants),
        )
        return {
            "product.template": dict.fromkeys(product_templates, taxes),
            "product.product": dict.fromkeys(product_variants, taxes),
        }

    @_debug.perf.timed
    def _post_load_demo_data(self, company=False):
        _debug.lifecycle("_post_load_demo_data", records=self)
        invoices = (
            self.ref("demo_invoice_1")
            + self.ref("demo_invoice_2")
            + self.ref("demo_invoice_3")
            + self.ref("demo_invoice_followup")
            + self.ref("demo_invoice_5")
            + self.ref("demo_invoice_6")
            + self.ref("demo_invoice_7")
            + self.ref("demo_invoice_8")
            + self.ref("demo_invoice_equipment_purchase")
            + self.ref("demo_invoice_9")
            + self.ref("demo_invoice_10")
            + self.ref("demo_move_auto_reconcile_1")
            + self.ref("demo_move_auto_reconcile_2")
            + self.ref("demo_move_auto_reconcile_3")
            + self.ref("demo_move_auto_reconcile_4")
            + self.ref("demo_move_auto_reconcile_5")
            + self.ref("demo_move_auto_reconcile_6")
            + self.ref("demo_move_auto_reconcile_7")
        )

        _debug.pipeline("demo_posting", invoices=invoices)
        for move in invoices:
            try:
                move.action_post()
            except UserError, ValidationError:
                _logger.exception("Error while posting demo data")

    @api.model
    def _prepare_demo_data_bank(self, company=False):
        if company.root_id.partner_id.bank_ids:
            return {}
        return {
            "demo_bank_1": {
                "acc_number": f"BANK{company.id}34567890",
                "partner_id": company.root_id.partner_id.id,
                "journal_id": "bank",
                "allow_out_payment": True,
            },
        }

    @api.model
    def _prepare_demo_data_partner(self):
        if self.env.ref("base.res_partner_2", raise_if_not_found=False):
            return {}
        return {
            "base.res_partner_2": {"name": "Demo Partner 2"},
            "base.res_partner_3": {"name": "Demo Partner 3"},
            "base.res_partner_4": {"name": "Demo Partner 4"},
            "base.res_partner_5": {"name": "Demo Partner 5"},
            "base.res_partner_6": {"name": "Demo Partner 6"},
            "base.res_partner_12": {"name": "Demo Partner 12"},
            "base.partner_demo": {"name": "Marc Demo"},
        }

    @api.model
    def _prepare_demo_data_user(self):
        if self.env.ref("base.user_demo", raise_if_not_found=False):
            return {}
        return {"base.user_demo": {"name": "Marc Demo", "login": "demo"}}

    @api.model
    def _prepare_demo_data_product(self):
        if self.env.ref("product.product_delivery_01", raise_if_not_found=False):
            return {}
        return {
            "product.product_delivery_01": {
                "name": "product_delivery_01",
                "type": "consu",
            },
            "product.product_delivery_02": {
                "name": "product_delivery_02",
                "type": "consu",
            },
            "product.consu_delivery_01": {"name": "consu_delivery_01", "type": "consu"},
            "product.consu_delivery_02": {"name": "consu_delivery_02", "type": "consu"},
            "product.consu_delivery_03": {"name": "consu_delivery_03", "type": "consu"},
            "product.product_order_01": {"name": "product_order_01", "type": "consu"},
        }

    @api.model
    def _prepare_demo_data_journal(self, company=False):
        if company.partner_id.bank_ids:
            return {
                "bank": {
                    "bank_account_id": company.partner_id.bank_ids[0].id,
                }
            }
        return {}

    @api.model
    @_debug.perf.timed
    def _prepare_demo_data_move(self, company=False):
        one_month_ago = fields.Date.today() + relativedelta(months=-1)
        cid = company.id or self.env.company.id
        misc_journal = self.env["account.journal"].search(
            domain=[
                *self.env["account.journal"]._check_company_domain(cid),
                ("type", "=", "general"),
            ],
            limit=1,
        )
        bank_journal = self.env["account.journal"].search(
            domain=[
                *self.env["account.journal"]._check_company_domain(cid),
                ("type", "=", "bank"),
            ],
            limit=1,
        )
        default_receivable = self.env.company.partner_id.with_company(
            company or self.env.company
        ).property_account_receivable_id
        income_account = (
            self.env["account.account"]
            .with_company(company or self.env.company)
            .search(
                [
                    *self.env["account.account"]._check_company_domain(cid),
                    ("account_type", "=", "income"),
                    (
                        "id",
                        "!=",
                        (
                            company or self.env.company
                        ).account_journal_early_pay_discount_gain_account_id.id,
                    ),
                ],
                limit=1,
            )
        )
        _debug.pipeline(
            "demo_move_accounts_resolved",
            company=cid,
            misc_journal=misc_journal,
            bank_journal=bank_journal,
            receivable=default_receivable,
            income_account=income_account,
        )
        return {
            **self._prepare_demo_data_move_invoices_1_3(),
            **self._prepare_demo_data_move_invoices_followup_6(),
            **self._prepare_demo_data_move_invoices_7_equipment(),
            **self._prepare_demo_data_move_invoices_9_10(),
            **self._prepare_demo_data_move_auto_reconcile_1_4(one_month_ago),
            **self._prepare_demo_data_move_auto_reconcile_5_7(
                misc_journal, bank_journal, default_receivable, income_account
            ),
        }

    @api.model
    @_debug.perf.timed
    def _prepare_demo_data_move_invoices_1_3(self):
        return {
            self.company_xmlid("demo_invoice_1"): {
                "move_type": "out_invoice",
                "partner_id": "base.res_partner_12",
                "invoice_user_id": "base.user_demo",
                "invoice_payment_term_id": "account.account_payment_term_end_following_month",
                "invoice_date": time.strftime("%Y-%m-01"),
                "delivery_date": time.strftime("%Y-%m-01"),
                "invoice_line_ids": [
                    Command.create(
                        {"product_id": "product.consu_delivery_02", "quantity": 5}
                    ),
                    Command.create(
                        {"product_id": "product.consu_delivery_03", "quantity": 5}
                    ),
                ],
            },
            self.company_xmlid("demo_invoice_2"): {
                "move_type": "out_invoice",
                "partner_id": "base.res_partner_2",
                "invoice_user_id": False,
                "invoice_date": (fields.Date.today() + timedelta(days=-2)).strftime(
                    "%Y-%m-%d"
                ),
                "delivery_date": (fields.Date.today() + timedelta(days=-2)).strftime(
                    "%Y-%m-%d"
                ),
                "invoice_line_ids": [
                    Command.create(
                        {"product_id": "product.consu_delivery_03", "quantity": 5}
                    ),
                    Command.create(
                        {"product_id": "product.consu_delivery_01", "quantity": 20}
                    ),
                ],
            },
            self.company_xmlid("demo_invoice_3"): {
                "move_type": "out_invoice",
                "partner_id": "base.res_partner_2",
                "invoice_user_id": False,
                "invoice_date": (fields.Date.today() + timedelta(days=-3)).strftime(
                    "%Y-%m-%d"
                ),
                "delivery_date": (fields.Date.today() + timedelta(days=-3)).strftime(
                    "%Y-%m-%d"
                ),
                "invoice_line_ids": [
                    Command.create(
                        {"product_id": "product.consu_delivery_01", "quantity": 5}
                    ),
                    Command.create(
                        {"product_id": "product.consu_delivery_03", "quantity": 5}
                    ),
                ],
            },
        }

    @api.model
    @_debug.perf.timed
    def _prepare_demo_data_move_invoices_followup_6(self):
        return {
            self.company_xmlid("demo_invoice_followup"): {
                "move_type": "out_invoice",
                "partner_id": "base.res_partner_2",
                "invoice_user_id": "base.user_demo",
                "invoice_payment_term_id": "account.account_payment_term_immediate",
                "invoice_date": (fields.Date.today() + timedelta(days=-15)).strftime(
                    "%Y-%m-%d"
                ),
                "delivery_date": (fields.Date.today() + timedelta(days=-15)).strftime(
                    "%Y-%m-%d"
                ),
                "invoice_line_ids": [
                    Command.create(
                        {"product_id": "product.consu_delivery_02", "quantity": 5}
                    ),
                    Command.create(
                        {"product_id": "product.consu_delivery_03", "quantity": 5}
                    ),
                ],
            },
            self.company_xmlid("demo_invoice_5"): {
                "move_type": "out_invoice",
                "partner_id": "base.res_partner_5",
                "invoice_user_id": "base.user_demo",
                "invoice_payment_term_id": "account.account_payment_term_end_following_month",
                "invoice_date": (fields.Date.today() + timedelta(days=-40)).strftime(
                    "%Y-%m-%d"
                ),
                "delivery_date": (fields.Date.today() + timedelta(days=-40)).strftime(
                    "%Y-%m-%d"
                ),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": "product.product_order_01",
                            "price_unit": 200,
                            "quantity": 10,
                        }
                    ),
                ],
            },
            self.company_xmlid("demo_invoice_6"): {
                "move_type": "out_invoice",
                "partner_id": "base.res_partner_5",
                "invoice_user_id": "base.user_demo",
                "invoice_payment_term_id": "account.account_payment_term_end_following_month",
                "invoice_date": (fields.Date.today() + timedelta(days=-35)).strftime(
                    "%Y-%m-%d"
                ),
                "delivery_date": (fields.Date.today() + timedelta(days=-35)).strftime(
                    "%Y-%m-%d"
                ),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": "product.product_order_01",
                            "price_unit": 100.0,
                            "quantity": 10,
                        }
                    ),
                ],
            },
        }

    @api.model
    @_debug.perf.timed
    def _prepare_demo_data_move_invoices_7_equipment(self):
        return {
            self.company_xmlid("demo_invoice_7"): {
                "move_type": "out_invoice",
                "partner_id": "base.res_partner_5",
                "invoice_user_id": "base.user_demo",
                "invoice_payment_term_id": "account.account_payment_term_end_following_month",
                "invoice_date": (
                    fields.Date.today() + relativedelta(months=-1)
                ).strftime("%Y-%m-%d"),
                "delivery_date": (
                    fields.Date.today() + relativedelta(months=-1)
                ).strftime("%Y-%m-%d"),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": "product.product_order_01",
                            "price_unit": 275,
                            "quantity": 1,
                        }
                    ),
                ],
            },
            self.company_xmlid("demo_invoice_8"): {
                "move_type": "in_invoice",
                "partner_id": "base.res_partner_4",
                "invoice_payment_term_id": "account.account_payment_term_end_following_month",
                "invoice_date": time.strftime("%Y-%m-01"),
                "delivery_date": time.strftime("%Y-%m-01"),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": "product.product_order_01",
                            "price_unit": 10.0,
                            "quantity": 1,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": "product.product_delivery_01",
                            "price_unit": 4,
                            "quantity": 5,
                        }
                    ),
                ],
                "message_main_attachment_id": "ir_attachment_in_invoice_1",
            },
            self.company_xmlid("demo_invoice_equipment_purchase"): {
                "move_type": "in_invoice",
                "ref": f"INV/{(fields.Date.today() + timedelta(days=-20)).year}/0057",
                "partner_id": "base.res_partner_3",
                "invoice_user_id": False,
                "invoice_date": (fields.Date.today() + timedelta(days=-20)).strftime(
                    "%Y-%m-%d"
                ),
                "delivery_date": (fields.Date.today() + timedelta(days=-20)).strftime(
                    "%Y-%m-%d"
                ),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Redeem Reference Number: PO02529",
                            "quantity": 1,
                            "price_unit": 622.27,
                        }
                    ),
                ],
                "message_main_attachment_id": "ir_attachment_in_invoice_2",
            },
        }

    @api.model
    @_debug.perf.timed
    def _prepare_demo_data_move_invoices_9_10(self):
        return {
            self.company_xmlid("demo_invoice_9"): {
                "move_type": "out_invoice",
                "partner_id": "base.res_partner_6",
                "invoice_user_id": False,
                "invoice_date": time.strftime("%Y-%m-%d"),
                "delivery_date": time.strftime("%Y-%m-%d"),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": "product.product_delivery_02",
                            "price_unit": 50.00,
                            "quantity": 15,
                        }
                    ),
                ],
            },
            self.company_xmlid("demo_invoice_10"): {
                "move_type": "out_invoice",
                "partner_id": "base.res_partner_5",
                "invoice_user_id": False,
                "invoice_date": (fields.Date.today() + timedelta(days=-5)).strftime(
                    "%Y-%m-%d"
                ),
                "delivery_date": (fields.Date.today() + timedelta(days=-5)).strftime(
                    "%Y-%m-%d"
                ),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": "product.consu_delivery_03",
                            "price_unit": 1799,
                            "quantity": 1,
                        }
                    ),
                ],
            },
        }

    @api.model
    @_debug.perf.timed
    def _prepare_demo_data_move_auto_reconcile_1_4(self, one_month_ago):
        return {
            self.company_xmlid("demo_move_auto_reconcile_1"): {
                "move_type": "out_refund",
                "partner_id": "base.res_partner_12",
                "invoice_date": one_month_ago.strftime("%Y-%m-02"),
                "delivery_date": one_month_ago.strftime("%Y-%m-02"),
                "invoice_line_ids": [
                    Command.create(
                        {"product_id": "product.consu_delivery_03", "quantity": 5}
                    ),
                ],
            },
            self.company_xmlid("demo_move_auto_reconcile_2"): {
                "move_type": "out_refund",
                "partner_id": "base.res_partner_12",
                "invoice_date": one_month_ago.strftime("%Y-%m-03"),
                "delivery_date": one_month_ago.strftime("%Y-%m-03"),
                "invoice_line_ids": [
                    Command.create(
                        {"product_id": "product.consu_delivery_02", "quantity": 5}
                    ),
                ],
            },
            self.company_xmlid("demo_move_auto_reconcile_3"): {
                "move_type": "in_refund",
                "partner_id": "base.res_partner_4",
                "invoice_date": time.strftime("%Y-%m-01"),
                "delivery_date": time.strftime("%Y-%m-01"),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": "product.product_delivery_01",
                            "price_unit": 10.0,
                            "quantity": 1,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": "product.product_order_01",
                            "price_unit": 4.0,
                            "quantity": 5,
                        }
                    ),
                ],
                "message_main_attachment_id": "ir_attachment_in_invoice_1",
            },
            self.company_xmlid("demo_move_auto_reconcile_4"): {
                "move_type": "out_refund",
                "partner_id": "base.res_partner_2",
                "invoice_date": (fields.Date.today() + timedelta(days=-10)).strftime(
                    "%Y-%m-%d"
                ),
                "delivery_date": (fields.Date.today() + timedelta(days=-10)).strftime(
                    "%Y-%m-%d"
                ),
                "invoice_line_ids": [
                    Command.create(
                        {"product_id": "product.consu_delivery_02", "quantity": 5}
                    ),
                    Command.create(
                        {"product_id": "product.consu_delivery_03", "quantity": 5}
                    ),
                ],
            },
        }

    @api.model
    @_debug.perf.timed
    def _prepare_demo_data_move_auto_reconcile_5_7(
        self, misc_journal, bank_journal, default_receivable, income_account
    ):
        return {
            self.company_xmlid("demo_move_auto_reconcile_5"): {
                "move_type": "out_refund",
                "partner_id": "base.res_partner_2",
                "invoice_date": (fields.Date.today() + timedelta(days=-2)).strftime(
                    "%Y-%m-%d"
                ),
                "delivery_date": (fields.Date.today() + timedelta(days=-2)).strftime(
                    "%Y-%m-%d"
                ),
                "invoice_line_ids": [
                    Command.create(
                        {"product_id": "product.consu_delivery_01", "quantity": 5}
                    ),
                    Command.create(
                        {"product_id": "product.consu_delivery_03", "quantity": 5}
                    ),
                ],
            },
            self.company_xmlid("demo_move_auto_reconcile_6"): {
                "move_type": "entry",
                "partner_id": "base.res_partner_2",
                "date": (fields.Date.today() + timedelta(days=-20)).strftime(
                    "%Y-%m-%d"
                ),
                "journal_id": misc_journal.id,
                "line_ids": [
                    Command.create(
                        {
                            "debit": 0.0,
                            "credit": 2500.0,
                            "account_id": default_receivable.id,
                        }
                    ),
                    Command.create(
                        {
                            "debit": 2500.0,
                            "credit": 0.0,
                            "account_id": bank_journal.default_account_id.id,
                        }
                    ),
                ],
            },
            self.company_xmlid("demo_move_auto_reconcile_7"): {
                "move_type": "entry",
                "partner_id": "base.res_partner_2",
                "date": (fields.Date.today() + timedelta(days=-20)).strftime(
                    "%Y-%m-%d"
                ),
                "journal_id": misc_journal.id,
                "line_ids": [
                    Command.create(
                        {
                            "debit": 2500.0,
                            "credit": 0.0,
                            "account_id": default_receivable.id,
                        }
                    ),
                    Command.create(
                        {
                            "debit": 0.0,
                            "credit": 2500.0,
                            "account_id": income_account.id,
                        }
                    ),
                ],
            },
        }

    @api.model
    @_debug.perf.timed
    def _prepare_demo_data_statement(self, company=False):
        cid = company.id or self.env.company.id
        bnk_journal = self.env["account.journal"].search(
            domain=[
                *self.env["account.journal"]._check_company_domain(cid),
                ("type", "=", "bank"),
            ],
            limit=1,
        )
        _debug.pipeline("demo_statement_journal", company=cid, journal=bnk_journal)
        return {
            "demo_bank_statement_1": {
                "name": "Opening Statement: First Synchronization",
                "balance_end_real": 4253.0,
                "balance_start": 5103.0,
                "attachment_ids": [Command.set(["ir_attachment_bank_statement_1"])],
                "line_ids": [
                    Command.create(
                        {
                            "journal_id": bnk_journal.id,
                            "payment_ref": "Office rent",
                            "amount": -850.0,
                            "date": (
                                fields.Date.today() + relativedelta(months=-2)
                            ).strftime("%Y-%m-%d"),
                        }
                    ),
                ],
            },
            "demo_bank_statement_2": {
                "name": f"{bnk_journal.name} - {(fields.Date.today() + relativedelta(months=-1)).strftime('%Y-%m-%d')}",
                "balance_end_real": 6678.0,
                "balance_start": 4253.0,
                "attachment_ids": [Command.set(["ir_attachment_bank_statement_2"])],
                "line_ids": [
                    Command.create(
                        {
                            "journal_id": bnk_journal.id,
                            "payment_ref": "Office rent",
                            "amount": -850.0,
                            "date": (
                                fields.Date.today() + relativedelta(months=-1)
                            ).strftime("%Y-%m-%d"),
                        }
                    ),
                    Command.create(
                        {
                            "journal_id": bnk_journal.id,
                            "payment_ref": time.strftime(
                                "INV/%Y/00006 and INV/%Y/00007"
                            ),
                            "amount": 1275.0,
                            "date": (
                                fields.Date.today() + relativedelta(months=-1)
                            ).strftime("%Y-%m-%d"),
                            "partner_name": "Open Wood Inc.",
                        }
                    ),
                    Command.create(
                        {
                            "journal_id": bnk_journal.id,
                            "payment_ref": "Payment of your invoice #5",
                            "amount": 2000.0,
                            "date": (
                                fields.Date.today() + timedelta(days=-40)
                            ).strftime("%Y-%m-%d"),
                            "partner_name": "Open Wood Inc.",
                        }
                    ),
                ],
            },
        }

    @api.model
    @_debug.perf.timed
    def _prepare_demo_data_transactions(self, company=False):
        cid = company.id or self.env.company.id
        bnk_journal = self.env["account.journal"].search(
            domain=[
                *self.env["account.journal"]._check_company_domain(cid),
                ("type", "=", "bank"),
            ],
            limit=1,
        )
        _debug.pipeline("demo_transactions_journal", company=cid, journal=bnk_journal)
        return {
            "demo_bank_statement_line_0": {
                "journal_id": bnk_journal.id,
                "payment_ref": "BILL/2024/01/0001",
                "amount": -622.27,
                "partner_id": "base.res_partner_3",
            },
            "demo_bank_statement_line_1": {
                "journal_id": bnk_journal.id,
                "payment_ref": "Office rent",
                "amount": -850.0,
            },
            "demo_bank_statement_line_2": {
                "journal_id": bnk_journal.id,
                "payment_ref": "Prepayment for invoice #9",
                "amount": 650.0,
                "partner_name": "Open Wood Inc.",
            },
            "demo_bank_statement_line_3": {
                "journal_id": bnk_journal.id,
                "payment_ref": "Last Year Interests",
                "amount": 102.78,
            },
            "demo_bank_statement_line_4": {
                "journal_id": bnk_journal.id,
                "payment_ref": time.strftime("INV/%Y/00008"),
                "amount": 738.75,
                "partner_id": "base.res_partner_6",
            },
            "demo_bank_statement_line_5": {
                "journal_id": bnk_journal.id,
                "payment_ref": f"R:9772938  10/07 AX 9415116318 T:5 BRT: {formatLang(self.env, 100.0, digits=2)} C/ croip",
                "amount": 96.67,
            },
        }

    @api.model
    @_debug.perf.timed
    def _prepare_demo_data_reconcile_model(self, company=False):
        return {
            "reconcile_from_label": {
                "name": "Line with Bank Fees",
                "match_label": "contains",
                "match_label_param": "BRT",
                "line_ids": [
                    Command.create(
                        {
                            "label": "Due amount",
                            "account_id": self._get_demo_account(
                                "income",
                                "income",
                                self.env.company,
                            ).id,
                            "amount_type": "regex",
                            "amount_string": r"BRT: ([\d,.]+)",
                        }
                    ),
                    Command.create(
                        {
                            "label": "Bank Fees",
                            "account_id": self._get_demo_account(
                                "expense_finance",
                                "expense",
                                self.env.company,
                            ).id,
                            "amount_type": "percentage",
                            "amount_string": "100",
                        }
                    ),
                ],
            },
            "owner_current_account_model": {
                "name": "Owner's Current Account",
                "line_ids": [
                    Command.create(
                        {
                            "label": "Owner's Current Account",
                            "account_id": self._get_demo_account(
                                "owner_current_account",
                                "asset_receivable",
                                self.env.company,
                            ).id,
                            "amount_type": "percentage",
                            "amount_string": "100",
                        }
                    ),
                ],
            },
        }

    @api.model
    @_debug.perf.timed
    def _prepare_demo_data_attachment(self, company=False):
        return {
            "ir_attachment_in_invoice_1": {
                "type": "binary",
                "name": "in_invoice_yourcompany_demo.pdf",
                "res_model": "account.move",
                "res_id": "demo_invoice_8",
                "res_field": "invoice_pdf_report_file",
                "raw": file_open(
                    "account/static/demo/in_invoice_yourcompany_demo_1.pdf", "rb"
                ).read(),
            },
            "ir_attachment_in_invoice_2": {
                "type": "binary",
                "name": "in_invoice_yourcompany_demo.pdf",
                "res_model": "account.move",
                "res_id": "demo_invoice_equipment_purchase",
                "res_field": "invoice_pdf_report_file",
                "raw": file_open(
                    "account/static/demo/in_invoice_yourcompany_demo_2.pdf", "rb"
                ).read(),
            },
            "ir_attachment_bank_statement_1": {
                "type": "binary",
                "name": "bank_opening_statement.pdf",
                "res_model": "account.bank.statement",
                "res_id": "demo_bank_statement_1",
                "raw": file_open(
                    "account/static/demo/bank_opening_statement.pdf", "rb"
                ).read(),
            },
            "ir_attachment_bank_statement_2": {
                "type": "binary",
                "name": "bank_statement_one_month_old.pdf",
                "res_model": "account.bank.statement",
                "res_id": "demo_bank_statement_2",
                "raw": file_open(
                    "account/static/demo/bank_statement_one_month_old.pdf", "rb"
                ).read(),
            },
        }

    @api.model
    @_debug.perf.timed
    def _prepare_demo_data_mail_message(self, company=False):
        return {
            "mail_message_in_invoice_1": {
                "model": "account.move",
                "res_id": "demo_invoice_8",
                "body": "Vendor Bill attachment",
                "message_type": "comment",
                "author_id": "base.partner_demo",
                "attachment_ids": [
                    Command.set(
                        [
                            "ir_attachment_in_invoice_1",
                        ]
                    )
                ],
            },
            "mail_message_in_invoice_2": {
                "model": "account.move",
                "res_id": "demo_invoice_equipment_purchase",
                "body": "Vendor Bill attachment",
                "message_type": "comment",
                "author_id": "base.partner_demo",
                "attachment_ids": [
                    Command.set(
                        [
                            "ir_attachment_in_invoice_2",
                        ]
                    )
                ],
            },
            "mail_message_bank_statement_1": {
                "model": "account.bank.statement",
                "res_id": "demo_bank_statement_1",
                "body": "Bank Statement attachment",
                "message_type": "comment",
                "author_id": "base.partner_demo",
                "attachment_ids": [
                    Command.set(
                        [
                            "ir_attachment_bank_statement_1",
                        ]
                    )
                ],
            },
            "mail_message_bank_statement_2": {
                "model": "account.bank.statement",
                "res_id": "demo_bank_statement_2",
                "body": "Bank Statement attachment",
                "message_type": "comment",
                "author_id": "base.partner_demo",
                "attachment_ids": [
                    Command.set(
                        [
                            "ir_attachment_bank_statement_2",
                        ]
                    )
                ],
            },
        }

    @api.model
    @_debug.perf.timed
    def _prepare_demo_data_mail_activity(self, company=False):
        return {
            "invoice_activity_1": {
                "res_id": "demo_invoice_3",
                "res_model_id": "account.model_account_move",
                "activity_type_id": "mail.mail_activity_data_todo",
                "date_deadline": (
                    fields.Datetime.today() + relativedelta(days=5)
                ).strftime("%Y-%m-%d %H:%M"),
                "summary": "Follow-up on payment",
                "create_uid": "base.user_admin",
                "user_id": "base.user_admin",
            },
            "invoice_activity_2": {
                "res_id": "demo_invoice_2",
                "res_model_id": "account.model_account_move",
                "activity_type_id": "mail.mail_activity_data_call",
                "date_deadline": fields.Datetime.today().strftime("%Y-%m-%d %H:%M"),
                "summary": "Follow up on missed call",
                "create_uid": "base.user_admin",
                "user_id": "base.user_admin",
            },
            "invoice_activity_3": {
                "res_id": "demo_invoice_1",
                "res_model_id": "account.model_account_move",
                "activity_type_id": "mail.mail_activity_data_todo",
                "date_deadline": (
                    fields.Datetime.today() + relativedelta(days=5)
                ).strftime("%Y-%m-%d %H:%M"),
                "summary": "Include upsell",
                "create_uid": "base.user_admin",
                "user_id": "base.user_admin",
            },
            "invoice_activity_4": {
                "res_id": "demo_invoice_8",
                "res_model_id": "account.model_account_move",
                "activity_type_id": "mail.mail_activity_data_todo",
                "date_deadline": (
                    fields.Datetime.today() + relativedelta(days=5)
                ).strftime("%Y-%m-%d %H:%M"),
                "summary": "Update address",
                "create_uid": "base.user_admin",
                "user_id": "base.user_admin",
            },
        }

    @api.model
    @_debug.perf.timed
    def _get_demo_account(self, xml_id, account_type, company):
        return (
            self.env["account.account"].browse(
                self.env["ir.model.data"]
                .sudo()
                .search(
                    [
                        ("name", "=", "%d_%s" % (company.id, xml_id)),
                        ("model", "=", "account.account"),
                    ],
                    limit=1,
                )
                .res_id
            )
            or self.env["account.account"]
            .with_company(company)
            .search(
                [
                    *self.env["account.account"]._check_company_domain(company),
                    ("account_type", "=", account_type),
                ],
                limit=1,
            )
            or self.env["account.account"]
            .with_company(company)
            .search(
                [
                    *self.env["account.account"]._check_company_domain(company),
                ],
                limit=1,
            )
        )
