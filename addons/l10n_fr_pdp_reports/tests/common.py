from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', 'post_install_l10n')
class PdpTestCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({
            "name": "PDP Test Company",
            "country_id": cls.env.ref("base.fr").id,
            "currency_id": cls.env.ref("base.EUR").id,
            "l10n_fr_pdp_enabled": True,
            "l10n_fr_pdp_route_code": "ROUTE",
            "l10n_fr_pdp_periodicity": "decade",
            "l10n_fr_pdp_payment_periodicity": "monthly",
            "siret": "12345678900000",
        })
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=[cls.company.id], force_company=cls.company.id))
        cls.company.partner_id.write({
            "vat": "FR23334175221",
            "country_id": cls.env.ref("base.fr").id,
        })
        cls.company._l10n_fr_pdp_ensure_journal()

        # Accounts
        cls.income_account = cls.env["account.account"].create({
            "name": "PDP Revenue",
            "code": "PDP100",
            "account_type": "income",
            "company_id": cls.company.id,
        })
        receivable = cls.env["account.account"].create({
            "name": "PDP Receivable",
            "code": "PDP101",
            "account_type": "asset_receivable",
            "reconcile": True,
            "company_id": cls.company.id,
        })
        payable = cls.env["account.account"].create({
            "name": "PDP Payable",
            "code": "PDP102",
            "account_type": "liability_payable",
            "reconcile": True,
            "company_id": cls.company.id,
        })
        cls.bank_account = cls.env["account.account"].create({
            "name": "PDP Bank Account",
            "code": "PDPBANK",
            "account_type": "asset_cash",
            "reconcile": True,
            "company_id": cls.company.id,
        })

        cls.partner_b2c = cls.env["res.partner"].create({
            "name": "B2C Customer",
            "country_id": cls.env.ref("base.fr").id,
            "property_account_receivable_id": receivable.id,
            "property_account_payable_id": payable.id,
        })
        cls.partner_international = cls.env["res.partner"].create({
            "name": "International Customer",
            "country_id": cls.env.ref("base.be").id,
            "vat": "BE0477472701",  # valid BE VAT for tests
            "property_account_receivable_id": receivable.id,
            "property_account_payable_id": payable.id,
        })

        cls.tax_20 = cls.env["account.tax"].create({
            "name": "VAT 20",
            "amount": 20,
            "amount_type": "percent",
            "type_tax_use": "sale",
            "company_id": cls.company.id,
            "tax_group_id": cls.env["account.tax.group"].search([("country_id", "=", cls.env.ref("base.fr").id)], limit=1).id
                            or cls.env["account.tax.group"].create({
                                "name": "FR VAT",
                                "country_id": cls.env.ref("base.fr").id,
                            }).id,
        })
        cls.product = cls.env["product.product"].create({
            "name": "Test Product",
            "lst_price": 100,
            "taxes_id": [(6, 0, cls.tax_20.ids)],
            "company_id": cls.company.id,
            "property_account_income_id": cls.income_account.id,
        })
        cls.bank_journal = cls.env["account.journal"].create({
            "name": "PDP Bank",
            "code": "PDBK",
            "type": "bank",
            "company_id": cls.company.id,
            "default_account_id": cls.bank_account.id,
        })
        cls.company.write({
            "account_journal_payment_debit_account_id": cls.bank_account.id,
            "account_journal_payment_credit_account_id": cls.bank_account.id,
        })

        # Ensure a clean slate
        cls.env["l10n.fr.pdp.flow"].sudo().search([("company_id", "=", cls.company.id)]).unlink()

    def setUp(self):
        super().setUp()
        self.env["l10n.fr.pdp.flow"].sudo().search([("company_id", "=", self.company.id)]).unlink()
        self.env["account.move"].sudo().search([
            ("company_id", "=", self.company.id),
            ("move_type", "in", ("out_invoice", "out_refund", "out_receipt")),
            ("name", "like", "INV%"),
        ]).unlink()
        self.env["account.payment"].sudo().search([
            ("company_id", "=", self.company.id),
        ]).unlink()
        self.env["account.move"].sudo().search([
            ("company_id", "=", self.company.id),
            ("journal_id", "=", self.bank_journal.id),
            ("name", "like", "BNK%"),
        ]).unlink()
        # Reset company identifiers/settings that tests may tweak.
        self.company.write({
            "siret": "12345678900000",
            "country_id": self.env.ref("base.fr").id,
            "l10n_fr_pdp_enabled": True,
            "l10n_fr_pdp_route_code": "ROUTE",
            "l10n_fr_pdp_periodicity": "decade",
            "l10n_fr_pdp_payment_periodicity": "monthly",
            "l10n_fr_pdp_tax_due_code": "3",
            "l10n_fr_pdp_deadline_override_start": False,
            "l10n_fr_pdp_deadline_override_end": False,
            "l10n_fr_pdp_send_mode": "auto",
        })
        self.company.partner_id.write({
            "vat": "FR23334175221",
            "country_id": self.env.ref("base.fr").id,
        })

    # Helpers ---------------------------------------------------------------
    def _create_invoice(self, partner=None, date_val=None, sent=False):
        partner = partner or self.partner_b2c
        date_val = date_val or fields.Date.today()
        journal = self.env["account.journal"].with_context(force_company=None).search([
            ("type", "=", "sale"),
            ("company_id", "=", self.company.id),
        ], limit=1)
        if not journal:
            journal = self.env["account.journal"].create({
                "name": "PDP Sales",
                "code": "PDSA",
                "type": "sale",
                "company_id": self.company.id,
                "default_account_id": self.income_account.id,
            })
        move = self.env["account.move"].with_company(self.company.id).create({
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "invoice_date": date_val,
            "journal_id": journal.id,
            "invoice_line_ids": [(0, 0, {
                "product_id": self.product.id,
                "quantity": 1,
                "price_unit": 100,
                "tax_ids": [(6, 0, self.tax_20.ids)],
                "account_id": self.income_account.id,
            })],
        })
        move.action_post()
        if sent:
            move.is_move_sent = True
        return move

    def _run_aggregation(self):
        # Clean previous flows for deterministic assertions
        self.env["l10n.fr.pdp.flow"].sudo().search([("company_id", "=", self.company.id)]).unlink()
        aggregator = self.env["l10n.fr.pdp.flow.aggregator"]
        ctx = {k: v for k, v in self.env.context.items() if k != "force_company"}
        ctx.update({"mail_create_nolog": True, "tracking_disable": True})
        return aggregator.with_context(ctx)._cron_process_company(self.company)

    def _aggregate_company(self):
        """Run the PDP aggregator without clearing existing flows."""
        aggregator = self.env["l10n.fr.pdp.flow.aggregator"]
        ctx = {k: v for k, v in self.env.context.items() if k != "force_company"}
        ctx.update({"mail_create_nolog": True, "tracking_disable": True})
        return aggregator.with_context(ctx)._cron_process_company(self.company)

    def _get_single_flow(self):
        return self.env["l10n.fr.pdp.flow"].search([("company_id", "=", self.company.id)])

    def _create_payment_for_invoice(self, invoice, amount=None, pay_date=None):
        """Create and post a customer payment and reconcile with the invoice."""
        amount = amount or invoice.amount_total
        pay_date = pay_date or fields.Date.today()
        journal = self.bank_journal
        payment = self.env["account.payment"].with_context(mail_create_nolog=True, tracking_disable=True).with_company(self.company.id).create({
            "payment_type": "inbound",
            "partner_type": "customer",
            "partner_id": invoice.partner_id.id,
            "amount": amount,
            "date": pay_date,
            "journal_id": journal.id,
            "payment_method_id": self.env.ref("account.account_payment_method_manual_in").id,
        })
        payment.action_post()
        receivable_line = payment.line_ids.filtered(lambda l: l.account_id.account_type == "asset_receivable")
        if receivable_line:
            inv_receivable = invoice.line_ids.filtered(lambda l: l.account_id.account_type == "asset_receivable").account_id
            receivable_line.account_id = inv_receivable
        (invoice.line_ids + payment.line_ids).filtered(lambda l: l.account_id.reconcile and l.account_id.account_type == "asset_receivable").reconcile()
        return payment
