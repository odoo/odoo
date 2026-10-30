from contextlib import contextmanager
from unittest.mock import patch

from odoo import Command, fields
from odoo.models import BaseModel
from odoo.tests import freeze_time, new_test_user

from odoo.addons.l10n_pt_certification.tests.common import TestL10nPtCommon
from odoo.addons.l10n_pt_sale.models.l10n_pt_at_series import AT_SERIES_WORKING_DOCUMENT_SAFT_TYPE_MAP

SALE_REPORT = 'sale.action_report_saleorder'

# Working documents of the AT's demo SAF-T, saft_idemo599999999.xml, one chain, signed with the AT's demo
# key (AT_DEMO_PUBLIC_KEY verifies them): (document number, date, SystemEntryDate, gross total, signature).
AT_SAMPLE_WORKING_DOCUMENTS = [
    ('COF E1/1', '2017-09-13', '2017-09-13 16:34:56', 56.54, "0Z5205QyulzTiunymKhw4QY98kKWfohYzd+79pMujoRBItru0uDWtj6vQyLumInI5kUsvnGB/SMjRU1iqj1iEaumPwqqpgeZReEgH/9b2pOfoahBAt8vocnFOM/NxvDOoiYa61vz9zGdWZzWjDv1NWxQpYSNercF8PrQm0m0UtA="),
    ('COF E1/2', '2017-09-14', '2017-09-14 09:23:23', 548.10, "rzdj0UZfMWjUMTq+Ge1LUK3YeGxDTPEcUUTH9lVzizFnM6PB9fHpYxS7IvLc5CbBHZlldAEOv/6CcxFoE8RNoa8XOGaQbYAptHD0hEsUvMxlh23CuHiKRQVac9bDMiS1FAjrBcXA29w6DHpaVRO285PAR1RZBhnGC3j4DPzcyCo="),
]


class TestL10nPtSaleCommon(TestL10nPtCommon):
    """
    Base of the ``l10n_pt_sale`` suite.

    A quotation (OR) is issued -- numbered, signed and locked in one step -- when it first reaches the
    customer or another document. Confirming it from its form leaves it as issued and confirms a new
    sales order (NE) copied from it (D-6), issued in turn at its first print, send or invoice:
    ``confirm()`` is that back-office Confirm, ``confirm_in_place()`` the confirmation of the quotation
    itself, as portal sign & pay does. ``issue()`` issues orders as their first print would.
    """

    @classmethod
    def get_default_groups(cls):
        # The class's own user manages sales, as it manages accounting.
        return super().get_default_groups() | cls.quick_ref('sales_team.group_sale_manager')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ==== Users ====
        cls.salesman = new_test_user(
            cls.env,
            login='pt_salesman',
            groups='base.group_user,sales_team.group_sale_salesman',
            company_id=cls.company_pt.id,
            company_ids=[Command.set((cls.company_pt + cls.branch_pt).ids)],
        )
        cls.other_company_salesman = new_test_user(
            cls.env,
            login='pt_other_company_salesman',
            groups='base.group_user,sales_team.group_sale_salesman',
            company_id=cls.company_pt_2.id,
            company_ids=[Command.set(cls.company_pt_2.ids)],
        )

        # ==== AT series: quotations and sales orders, for 2026 ====
        cls.series_or = cls.series_factory(document_type='quotation')
        cls.series_ne = cls.series_factory(document_type='sales_order')

        # ==== Online payments: a provider paying into the bank journal of the RG series ====
        cls.payment_provider = cls.env['payment.provider'].create({
            'name': "Dummy Provider",
            'code': 'none',
            'state': 'test',
            'is_published': True,
            'company_id': cls.company_pt.id,
            'payment_method_ids': [Command.set(cls.env.ref('payment.payment_method_unknown').ids)],
        })
        cls._create_dummy_payment_method_for_provider(provider=cls.payment_provider, journal=cls.series_rg.journal_id)

    # -------------------------------------------------------------------------
    # Factories
    # -------------------------------------------------------------------------

    @classmethod
    def series_factory(cls, **overrides):
        """``TestL10nPtCommon.series_factory``; a quotation or sales order series has no journal."""
        if prefix := AT_SERIES_WORKING_DOCUMENT_SAFT_TYPE_MAP.get(overrides.get('document_type')):
            overrides = {'prefix': prefix, 'journal_id': False, **overrides}
        return super().series_factory(**overrides)

    @classmethod
    def make_order(cls, lines=None, partner=None, date_order=None, pricelist=None, company=None, **vals):
        """
        A quotation of ``company_pt``, dated now, to ``partner_pt``, with one 100.00 line of
        ``product_a`` at the company's 23 %, whose salesperson is ``salesman`` in the companies of that user.
        ``lines`` are the values of each line over those defaults, records allowed
        (``{'tax_ids': cls.tax_sale_exempt}``). Its AT series is left to the module to pick.
        """
        company = company or cls.company_pt
        partner = cls.partner_pt if partner is None else partner
        line_model = cls.env['sale.order.line']
        default_tax = (
            cls.env['account.chart.template'].with_company(company.root_id).ref('iva_pt_sale_normal', raise_if_not_found=False)
            or company.root_id.account_sale_tax_id
        )

        def line_vals(line):
            if line.get('display_type'):
                return line
            vals = {
                'product_id': cls.product_a.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
                'tax_ids': [Command.set(default_tax.ids)],
            }
            for field_name, value in line.items():
                if isinstance(value, BaseModel):
                    value = [Command.set(value.ids)] if line_model._fields[field_name].type == 'many2many' else value.id
                vals[field_name] = value
            return vals

        return cls.env['sale.order'].with_company(company).create({
            'company_id': company.id,
            'partner_id': partner.id,
            'date_order': date_order or fields.Datetime.now(),
            'user_id': cls.salesman.id if company in cls.salesman.company_ids else False,
            **({'pricelist_id': pricelist.id} if pricelist else {}),
            'order_line': [Command.create(line_vals(line)) for line in (lines or [{}])],
            **vals,
        })

    @classmethod
    def confirm(cls, quotation):
        """Confirm ``quotation`` from its form: it is issued as it stands, and the new sales order is returned."""
        action = quotation.action_l10n_pt_create_sales_order()
        return quotation.browse(action['res_id'])

    @classmethod
    def confirm_in_place(cls, quotation):
        """Confirm ``quotation`` itself, as portal sign & pay does."""
        quotation.action_confirm()
        return quotation

    @classmethod
    def send(cls, orders):
        """Open the send wizard of ``orders``, as the Send button does."""
        return orders.action_quotation_send()

    @classmethod
    def cancel(cls, orders, reason="Cliente desistiu"):
        """Cancel ``orders`` as the Cancel button does: issued ones through the cancel wizard, given ``reason``."""
        action = orders.action_cancel()
        if isinstance(action, dict) and action.get('res_model') == 'l10n_pt.cancel':
            wizard = orders.env['l10n_pt.cancel'].with_context(action['context']).create({'l10n_pt_cancel_reason': reason})
            wizard.button_cancel()
        return orders

    @classmethod
    def pay_online(cls, order, amount=None, automatic_invoice=True):
        """
        A transaction paying ``amount`` (all) of ``order`` online, confirmed by the provider and
        post-processed as `/payment/status/poll` does, with the Sales setting ``automatic_invoice``.
        """
        cls.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', str(automatic_invoice))
        transaction = cls.env['payment.transaction'].sudo().create({
            'provider_id': cls.payment_provider.id,
            'payment_method_id': cls.env.ref('payment.payment_method_unknown').id,
            'reference': f"{order.name}-{len(order.sudo().transaction_ids) + 1}",
            'amount': order.amount_total if amount is None else amount,
            'currency_id': order.currency_id.id,
            'partner_id': order.partner_id.id,
            'operation': 'online_redirect',
            'sale_order_ids': [Command.set(order.ids)],
        })
        transaction._set_done()
        transaction._post_process()
        return transaction

    @classmethod
    def invoice(cls, orders, method='delivered', amount=None):
        """
        The invoices the Create Invoice wizard makes for ``orders``, in their environment: the regular
        invoice (``delivered``), or a down payment (``percentage``, ``fixed``) of ``amount``.
        """
        invoices_before = orders.invoice_ids
        orders.env['sale.advance.payment.inv'].with_context(
            active_model='sale.order',
            active_ids=orders.ids,
        ).create({
            'advance_payment_method': method,
            **({'amount': amount} if method == 'percentage' else {}),
            **({'fixed_amount': amount} if method == 'fixed' else {}),
        }).create_invoices()
        return orders.invoice_ids - invoices_before

    @contextmanager
    def at_sample_orders(self):
        """
        The working documents of the AT's demo SAF-T (``AT_SAMPLE_WORKING_DOCUMENTS``), as quotations of
        a 2017 OR series, each issued at its SystemEntryDate and exempt of VAT, so that its gross total
        is its price. Yields ``{quotation: signature}``, the signature the AT published for each. The AT
        numbers them ``COF E1/1``, the module ``OR 2017/00001``: within the context, what is signed and
        verified carries the AT's number; every other value is the module's.
        """
        SaleOrder = self.registry['sale.order']
        get_document_number = SaleOrder._l10n_pt_get_document_number
        at_numbers, signatures = {}, {}

        def document_number(order):
            return at_numbers.get(order.id) or get_document_number(order)

        with patch.object(SaleOrder, '_l10n_pt_get_document_number', document_number):
            series = self.series_factory(name='2017', document_type='quotation', date_start='2017-01-01', date_end='2017-12-31')
            for number, document_date, system_entry_date, gross_total, signature in AT_SAMPLE_WORKING_DOCUMENTS:
                with freeze_time(system_entry_date):
                    quotation = self.make_order(
                        date_order=f'{document_date} 00:00:00',
                        lines=[{'price_unit': gross_total, 'tax_ids': self.tax_sale_exempt}],
                        l10n_pt_at_series_id=series.id,
                    )
                    at_numbers[quotation.id] = number
                    self.issue(quotation)
                signatures[quotation] = signature
            yield signatures

    @classmethod
    def print_pdf(cls, records, report=None):
        return super().print_pdf(records, report or (SALE_REPORT if records._name == 'sale.order' else None))

    @classmethod
    def preview(cls, records, report=None):
        return super().preview(records, report or (SALE_REPORT if records._name == 'sale.order' else None))
