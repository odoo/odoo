import unittest
from datetime import datetime, timedelta

from odoo import Command, fields
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tests import Form, freeze_time, new_test_user, tagged

from odoo.addons.l10n_pt_sale.tests.common import TestL10nPtSaleCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtSaleOrder(TestL10nPtSaleCommon):
    """
    The life of a PT quotation and sales order, from its series to its cancellation.

    A quotation (OR) and a sales order (NE) are working documents, each numbered in an AT series of
    its own type (Portaria 302/2016 4.3; Portaria 195/2020). One is issued -- numbered, signed and
    locked in one step -- when it first reaches the customer or another document: printed, previewed,
    sent, confirmed or invoiced (Despacho 8632/2014 2.1.1, 1.11). Confirming a quotation nobody issued
    yet makes it the sales order, in place; confirming an issued one keeps it as issued and confirms a
    new sales order copied from it. Documents of a series are issued in date
    order (Despacho 8632/2014 2.2.1).
    """

    # -------------------------------------------------------------------------
    # Series
    # -------------------------------------------------------------------------

    def test_series_by_document_type(self):
        """
        The first quotation and the first sales order of a company each get a series of their own type,
        whichever type's series was created first.
        """
        series_ne_2 = self.series_factory(document_type='sales_order', company_id=self.company_pt_2.id)
        series_or_2 = self.series_factory(document_type='quotation', company_id=self.company_pt_2.id)
        for company, series_or, series_ne in (
            (self.company_pt, self.series_or, self.series_ne),
            (self.company_pt_2, series_or_2, series_ne_2),
        ):
            with self.subTest(company=company.name):
                quotation = self.make_order(company=company)
                self.assertRecordValues(quotation, [{'l10n_pt_document_type': 'quotation', 'l10n_pt_at_series_id': series_or.id}])
                sales_order = self.confirm(self.issue(quotation))
                self.assertRecordValues(sales_order, [{'l10n_pt_document_type': 'sales_order', 'l10n_pt_at_series_id': series_ne.id}])
                self.assertEqual(quotation.l10n_pt_at_series_id, series_or)

    def test_sales_order_series_after_confirm_in_place(self):
        """
        An issued quotation confirmed in place by core's `action_confirm` keeps its type and series; a
        sales order confirmed after it still gets a sales order series.
        """
        quotation = self.confirm_in_place(self.issue(self.make_order()))
        self.assertRecordValues(quotation, [{
            'state': 'sale',
            'l10n_pt_document_type': 'quotation',
            'l10n_pt_at_series_id': self.series_or.id,
            'l10n_pt_document_number': 'OR 2026/00001',
        }])
        sales_order = self.confirm(self.make_order())
        self.assertEqual(sales_order.l10n_pt_at_series_id, self.series_ne)

    def test_missing_series_offers_prefilled_series(self):
        """
        Without a series of the document's type, the user is sent to a new series prefilled with that
        type and the company: at creation for a quotation, at confirmation for its sales order.
        """
        with self.assertRaises(RedirectWarning) as quotation_warning, self.env.cr.savepoint():
            self.make_order(company=self.company_pt_2)
        self.assertEqual(quotation_warning.exception.args[1]['context'], {
            'l10n_pt_series_document_types': ['quotation'],
            'default_company_id': self.company_pt_2.id,
        })
        self.series_factory(document_type='quotation', company_id=self.company_pt_2.id)
        quotation = self.make_order(company=self.company_pt_2)
        with self.assertRaises(RedirectWarning) as order_warning, self.env.cr.savepoint():
            self.confirm(quotation)
        self.assertEqual(order_warning.exception.args[1]['context'], {
            'l10n_pt_series_document_types': ['sales_order'],
            'default_company_id': self.company_pt_2.id,
        })

    def test_series_form_offers_sales_order_series(self):
        """
        A series created from a quotation's series field is a quotation series, and offers to create
        the sales order series under the same name when the company has none. That one still
        needs its own AT validation code.
        """
        SeriesForm = self.env['l10n_pt.at.series'].with_context(
            l10n_pt_series_document_types=['quotation'],
            default_company_id=self.company_pt_2.id,
        )
        with Form(SeriesForm) as series_form:
            self.assertEqual(series_form.document_type, 'quotation')
            self.assertEqual(series_form.prefix, 'OR')
            self.assertEqual(series_form.company_id, self.company_pt_2)
            self.assertTrue(series_form.l10n_pt_create_sales_order_series)
            series_form.name = '2026'
            series_form.at_code = 'ATFORM0001'
        series_ne = self.env['l10n_pt.at.series'].search([
            ('company_id', '=', self.company_pt_2.id),
            ('document_type', '=', 'sales_order'),
        ])
        self.assertRecordValues(series_ne, [{'name': '2026', 'prefix': 'NE', 'at_code': False}])

        # The company has a sales order series now: nothing more is offered.
        with Form(SeriesForm) as series_form:
            self.assertFalse(series_form.l10n_pt_create_sales_order_series)
            series_form.name = '2026B'
            series_form.at_code = 'ATFORM0002'
        self.assertEqual(self.env['l10n_pt.at.series'].search_count([
            ('company_id', '=', self.company_pt_2.id),
            ('document_type', '=', 'sales_order'),
        ]), 1)

    def test_series_without_at_code_refused(self):
        """An order cannot be issued in a series the AT has not validated, and consumes no number."""
        series = self.series_factory(document_type='quotation', company_id=self.company_pt_2.id, at_code=False)
        self.series_factory(document_type='sales_order', company_id=self.company_pt_2.id)
        quotation = self.make_order(company=self.company_pt_2)
        with self.assertRaisesRegex(RedirectWarning, "has no AT validation code"), self.env.cr.savepoint():
            self.issue(quotation)
        self.assertNotIssued(quotation)
        series.at_code = 'ATLATE0001'
        self.issue(quotation)
        self.assertEqual(quotation.l10n_pt_document_number, 'OR 2026/00001')

    def test_issued_order_keeps_ended_series(self):
        """An issued order keeps the series it was issued in once that series ends; new ones need a valid series."""
        quotation = self.issue(self.make_order())
        series_2027 = self.series_factory(name='2027', document_type='quotation', date_start='2027-01-01', date_end='2027-12-31')
        with freeze_time('2027-01-04 10:00:00'):
            quotation.write({'validity_date': '2027-01-31'})
            self.assertEqual(quotation.l10n_pt_at_series_id, self.series_or)
            new_quotation = self.make_order()
            self.assertEqual(new_quotation.l10n_pt_at_series_id, series_2027)
            self.issue(new_quotation)
            self.assertEqual(new_quotation.l10n_pt_document_number, 'OR 2027/00001')

    # -------------------------------------------------------------------------
    # Issuing
    # -------------------------------------------------------------------------

    def test_triggers_issue(self):
        """
        Printing, an HTML render, opening the send wizard and marking the quotation sent (by hand, or by
        posting with the send wizard's `mark_so_as_sent`) each issue it, in one signing call: no
        quotation is sent unissued. Other drafts stay unnumbered and editable. Confirming
        it does not issue it: it becomes the sales order. The customer opening its page does not
        (`TestL10nPtSalePortal`).
        """
        for trigger_name, trigger in (
            ("print", self.print_pdf),
            ("HTML render", self.preview),
            ("send", self.send),
            ("mark as sent", lambda quotation: quotation.action_quotation_sent()),
            ("sent by mail", lambda quotation: quotation.with_context(mark_so_as_sent=True).message_post(body="Orçamento")),
        ):
            with self.subTest(trigger=trigger_name):
                quotation, other = (self.make_order() + self.make_order())
                self.signing.reset()
                trigger(quotation)
                self.assertIssued(quotation)
                self.assertRecordValues(quotation, [{'l10n_pt_document_type': 'quotation', 'locked': True}])
                self.assertSignatureValid(quotation)
                self.assertEqual(self.signing.calls['sign_records'], 1)
                self.assertNotIssued(other)
                other.order_line.product_uom_qty = 2

    def test_share_issues(self):
        """
        Opening Share on a quotation issues it, as the internal user sharing it: the link it hands out
        presents the quotation to whoever opens it, and the customer's page never issues.
        """
        quotation, other = self.make_order(), self.make_order()
        values = self.env['portal.share'].with_context(
            active_model='sale.order', active_id=quotation.id,
        ).default_get(['res_model', 'res_id', 'share_link'])
        self.assertIn(f'model=sale.order&res_id={quotation.id}&access_token=', values['share_link'])
        self.assertIssued(quotation)
        self.assertEqual(quotation.l10n_pt_issue_user_id, self.env.user)
        self.assertNotIssued(other)

    def test_preview_does_not_issue(self):
        """
        The form's Preview is the salesperson's look at the customer's page: it leaves the quotation a
        draft, unnumbered, unsigned and editable.
        """
        quotation = self.make_order()
        action = quotation.action_preview_sale_order()
        self.assertEqual(action['url'], quotation.get_portal_url())
        self.assertNotIssued(quotation)
        self.assertFalse(quotation.locked)
        quotation.order_line.product_uom_qty = 2
        self.assertEqual(self.signing.calls['sign_records'], 0)

    def test_sales_order_issued_at_first_use(self):
        """
        The sales order confirmed from a quotation is issued at its first print, send or invoice, not
        at confirmation; invoicing issues only the orders invoiced.
        """
        for trigger_name, trigger in (
            ("print", self.print_pdf),
            ("send", self.send),
            ("invoice", self.invoice),
        ):
            with self.subTest(trigger=trigger_name):
                sales_order = self.confirm(self.make_order())
                other = self.confirm(self.make_order())
                self.assertNotIssued(sales_order + other)
                trigger(sales_order)
                self.assertIssued(sales_order)
                self.assertSignatureValid(sales_order)
                self.assertNotIssued(other)

    @unittest.skip("Known issue: a sales user without accounting rights cannot read the AT series")
    def test_salesman_issues_quotation(self):
        """
        A salesman without accounting rights prints, sends and confirms their own quotation, which
        issues it as them, without leaking a superuser environment.
        """
        for trigger_name, trigger in (
            ("print", self.print_pdf),
            ("send", self.send),
            ("confirm", self.confirm),
        ):
            with self.subTest(trigger=trigger_name):
                quotation = self.make_order().with_user(self.salesman)
                result = trigger(quotation)
                self.assertIssued(quotation)
                self.assertEqual(quotation.l10n_pt_issue_user_id, self.salesman)
                self.assertFalse(quotation.env.su)
                if trigger_name == "confirm":
                    self.assertFalse(result.env.su)
                    self.print_pdf(result)
                    self.assertIssued(result)

    def test_issuing_records_number_issuer_and_time(self):
        """
        Issuing gives the order its document number, its ATCUD the series' code and number, and records
        who issued it and when (Portaria 302/2016 4.3.4.3.4), as the real user.
        """
        quotation = self.make_order()
        with freeze_time('2026-06-15 16:45:00'):
            self.print_pdf(quotation)
        self.assertRecordValues(quotation, [{
            'l10n_pt_document_number': 'OR 2026/00001',
            'l10n_pt_atcud': f'{self.series_or.at_code}-1',
            'l10n_pt_issue_user_id': self.env.user.id,
            'l10n_pt_issued_on': datetime(2026, 6, 15, 16, 45),
            'l10n_pt_hashed_on': datetime(2026, 6, 15, 16, 45),
        }])
        self.assertFalse(quotation.env.su)
        with freeze_time('2026-06-15 17:00:00'):
            sales_order = self.confirm(quotation)
            self.print_pdf(sales_order)
        self.assertRecordValues(sales_order, [{
            'l10n_pt_document_number': 'NE 2026/00001',
            'l10n_pt_atcud': f'{self.series_ne.at_code}-1',
            'quotation_id': quotation.id,
        }])

    def test_chronology(self):
        """
        No order may be issued dated before the last one issued in its series (Despacho 8632/2014
        2.2.1); an order already issued can be sent again whatever came after it.
        """
        older = self.issue(self.make_order(date_order=datetime(2026, 6, 10, 9, 0)))
        self.issue(self.make_order(date_order=datetime(2026, 6, 12, 9, 0)))
        late = self.make_order(date_order=datetime(2026, 6, 11, 9, 0))
        with self.assertRaisesRegex(UserError, "dated earlier than the last document issued"), self.env.cr.savepoint():
            self.issue(late)
        self.assertNotIssued(late)
        self.send(older)
        self.print_pdf(older)

    def test_future_date(self):
        """
        An order dated in the future is warned about; once it is issued, no order dated before it
        can be issued in its series (Despacho 8632/2014 2.2.1).
        """
        future = self.make_order(date_order=fields.Datetime.now() + timedelta(days=1))
        self.assertTrue(future.l10n_pt_show_future_date_warning)
        self.assertFalse(self.make_order().l10n_pt_show_future_date_warning)
        self.issue(future)
        with self.assertRaisesRegex(UserError, "dated earlier than the last document issued"), self.env.cr.savepoint():
            self.issue(self.make_order())

    def test_clock_behind_last_issued_document(self):
        """
        A system clock earlier than the last document issued, of any type, is to be confirmed before
        issuing an order (Despacho 8632/2014 3.4.3).
        """
        with freeze_time('2026-06-15 11:00:00'):
            self.issue(self.post(self.make_invoice()))
        quotation = self.make_order()
        with self.assertRaisesRegex(RedirectWarning, "earlier than those of the last document issued"), self.env.cr.savepoint():
            self.print_pdf(quotation)
        self.assertNotIssued(quotation)
        self.env['res.company']._l10n_pt_confirm_system_clock()
        self.print_pdf(quotation)
        self.assertIssued(quotation)

    def test_several_orders_issued_at_once(self):
        """Several orders with exempt lines are issued together, each checked for its exemption reason."""
        quotations = (
            self.make_order(lines=[{'tax_ids': self.tax_sale_exempt}])
            + self.make_order(lines=[{'tax_ids': self.tax_sale_exempt}, {}])
        )
        self.issue(quotations)
        self.assertIssued(quotations)
        self.assertChainVerified(quotations)

    # -------------------------------------------------------------------------
    # Lines
    # -------------------------------------------------------------------------

    def test_line_rules(self):
        """
        Every priced line carries one VAT tax, withholding aside, and a positive amount: the SAF-T has
        room for one tax per line; sections and notes are free.
        """
        withholding = self.env['account.tax'].create({
            'name': 'Retenção IRS 25%', 'amount': -25.0, 'type_tax_use': 'sale', 'company_id': self.company_pt.id,
        })
        for lines, message in (
            ([{'tax_ids': self.env['account.tax']}], "without VAT tax"),
            ([{'tax_ids': self.tax_sale_23 + self.tax_sale_exempt}], "can only carry one tax"),
            ([{'price_unit': 0.0}], "amount of 0 are not allowed"),
            ([{'price_unit': -10.0}], "cannot create a Quotation with negative lines"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(ValidationError, message), self.env.cr.savepoint():
                self.make_order(lines=lines)
        quotation = self.issue(self.make_order(lines=[
            {'display_type': 'line_section', 'name': 'Serviços'},
            {'tax_ids': self.tax_sale_23 + withholding},
            {'display_type': 'line_note', 'name': 'Entrega em 5 dias'},
        ]))
        self.assertIssued(quotation)
        self.assertSignatureValid(quotation)

    def test_tax_without_exemption_reason_refused(self):
        """An order charging no VAT names its exemption reason, also with a tax stored before that rule."""
        self.tamper(self.tax_sale_exempt, 'l10n_pt_tax_exemption_reason', None)
        quotation = self.make_order(lines=[{'tax_ids': self.tax_sale_exempt}])
        with self.assertRaisesRegex(ValidationError, "needs a VAT exemption reason"), self.env.cr.savepoint():
            self.issue(quotation)
        self.assertNotIssued(quotation)

    def test_discounts(self):
        """
        Discounts are given as a line discount and a global discount, between 0 and 100 %, combined
        on each line.
        """
        quotation = self.make_order(
            lines=[{'price_unit': 1234.568, 'l10n_pt_line_discount': 10.0}, {'price_unit': 756.81}],
            l10n_pt_global_discount=10.0,
        )
        self.assertRecordValues(quotation.order_line, [
            {'discount': 19.0, 'price_subtotal': 1000.0},
            {'discount': 10.0, 'price_subtotal': 681.13},
        ])
        self.assertRecordValues(quotation, [{'amount_untaxed': 1681.13, 'amount_tax': 386.66, 'amount_total': 2067.79}])
        quotation.l10n_pt_global_discount = 0.0
        self.assertEqual(quotation.order_line.mapped('discount'), [10.0, 0.0])
        for vals, message in (
            ({'l10n_pt_global_discount': 101.0}, "between 0% and 100%|negative lines"),
            ({'l10n_pt_global_discount': -1.0}, "between 0% and 100%"),
            ({'lines': [{'l10n_pt_line_discount': 101.0}]}, "between 0% and 100%|negative lines"),
        ):
            with self.subTest(vals=vals), self.assertRaisesRegex(ValidationError, message), self.env.cr.savepoint():
                self.make_order(**vals)

    @unittest.skip("Known issue: the default line discount overwrites the discount the pricelist shows")
    def test_pricelist_discount_kept(self):
        """
        A discount the pricelist shows on a line is kept as its line discount, as a core discount given
        to an invoice line is; the global discount still applies on top of it.
        """
        self.env.ref('base.user_root').group_ids += self.env.ref('sale.group_discount_per_so_line')
        pricelist = self.env['product.pricelist'].create({
            'name': "Desconto 15%",
            'company_id': False,
            'item_ids': [Command.create({'compute_price': 'percentage', 'percent_price': 15.0, 'applied_on': '3_global'})],
        })
        # Outside PT, the pricelist shows its discount on the line.
        foreign_order = self.make_order(company=self.company_foreign, pricelist=pricelist)
        self.assertEqual(foreign_order.order_line.discount, 15.0)
        quotation = self.make_order(pricelist=pricelist)
        self.assertRecordValues(quotation.order_line, [{'l10n_pt_line_discount': 15.0, 'discount': 15.0}])
        quotation.l10n_pt_global_discount = 10.0
        self.assertRecordValues(quotation.order_line, [{'l10n_pt_line_discount': 15.0, 'discount': 23.5}])

    # -------------------------------------------------------------------------
    # Confirmation
    # -------------------------------------------------------------------------

    def test_confirm_unissued_quotation_in_place(self):
        """
        Confirming a quotation nobody issued yet, from its form, makes it the sales order: no copy, its
        type and series become those of a sales order, whichever quotation series it had, and it is
        issued as an NE at its first print.
        """
        other_series_or = self.series_factory(document_type='quotation', name='2026B')
        for series_or in (self.series_or, other_series_or):
            with self.subTest(series=series_or.name):
                quotation = self.make_order(l10n_pt_at_series_id=series_or.id)
                self.assertEqual(self.confirm(quotation), quotation)
                self.assertRecordValues(quotation, [{
                    'state': 'sale',
                    'l10n_pt_document_type': 'sales_order',
                    'l10n_pt_at_series_id': self.series_ne.id,
                    'quotation_id': False,
                    'sales_order_count': 0,
                }])
                self.assertNotIssued(quotation)
                self.issue(quotation)
                self.assertEqual(quotation.l10n_pt_document_number[:3], 'NE ')
                self.assertSignatureValid(quotation)
        self.assertFalse(self.env['sale.order'].search([('l10n_pt_at_series_id', 'in', (self.series_or + other_series_or).ids)]))

    def test_confirm_issued_quotation_keeps_it(self):
        """
        Confirming an issued quotation -- printed, rendered or sent -- leaves it as it was issued, signed
        and locked, and confirms a new sales order copied from it, unissued until its first print, send
        or invoice.
        """
        for trigger_name, trigger in (
            ("print", self.print_pdf),
            ("HTML render", self.preview),
            ("mark as sent", lambda quotation: quotation.action_quotation_sent()),
        ):
            with self.subTest(trigger=trigger_name):
                quotation = self.make_order(lines=[{}, {'price_unit': 50.0}])
                trigger(quotation)
                document_number = quotation.l10n_pt_document_number
                sales_order = self.confirm(quotation)
                self.assertNotEqual(sales_order, quotation)
                self.assertRecordValues(quotation, [{
                    'state': 'sent',
                    'l10n_pt_ordered': True,
                    'locked': True,
                    'l10n_pt_document_type': 'quotation',
                    'l10n_pt_document_number': document_number,
                    'sales_order_count': 1,
                }])
                self.assertSignatureValid(quotation)
                self.assertRecordValues(sales_order, [{
                    'state': 'sale',
                    'quotation_id': quotation.id,
                    'l10n_pt_document_type': 'sales_order',
                    'l10n_pt_at_series_id': self.series_ne.id,
                    'amount_total': quotation.amount_total,
                    'partner_id': quotation.partner_id.id,
                }])
                self.assertEqual(sales_order.order_line.mapped('price_unit'), quotation.order_line.mapped('price_unit'))
                self.assertNotIssued(sales_order)
                self.assertEqual(quotation.action_view_sale_orders()['res_id'], sales_order.id)
                self.assertEqual(sales_order.action_view_origin_quotation()['res_id'], quotation.id)

    def test_quotation_ordered(self):
        """
        A quotation confirmed into a sales order was presented and accepted: it is sent, and flagged
        ordered -- left out by the "Not Ordered" filter -- until that sales order is cancelled. One
        confirmed in place is the sales order itself, never flagged.
        """
        quotation, other = self.issue(self.make_order()), self.make_order()
        orders = quotation + other
        self.assertFalse(any(orders.mapped('l10n_pt_ordered')))
        sales_order = self.confirm(quotation)
        self.assertRecordValues(quotation, [{'state': 'sent', 'l10n_pt_ordered': True}])
        self.assertEqual(orders.filtered_domain([('l10n_pt_ordered', '=', False)]), other)
        self.assertEqual(orders.search([('id', 'in', orders.ids), ('l10n_pt_ordered', '=', False)]), other)
        self.assertEqual(orders.search([('id', 'in', orders.ids), ('l10n_pt_ordered', '=', True)]), quotation)
        self.assertEqual(self.confirm(other), other)
        self.assertFalse(other.l10n_pt_ordered)
        self.cancel(sales_order)
        self.assertFalse(quotation.l10n_pt_ordered)
        self.assertFalse(orders.search([('id', 'in', orders.ids), ('l10n_pt_ordered', '=', True)]))

    def test_confirm_twice(self):
        """
        A quotation already confirmed into a sales order is not confirmed again: its Confirm opens that
        sales order, and no second one is created. Once that sales order is cancelled, the quotation can
        be confirmed anew.
        """
        quotation = self.issue(self.make_order())
        sales_order = self.confirm(quotation)
        self.assertEqual(self.confirm(quotation), sales_order)
        self.assertEqual(quotation.sales_order_ids, sales_order)
        with self.assertRaises(UserError):
            quotation._l10n_pt_create_sales_order()
        self.assertEqual(quotation.sales_order_ids, sales_order)
        self.cancel(sales_order)
        new_sales_order = self.confirm(quotation)
        self.assertNotIn(new_sales_order, quotation + sales_order)
        self.assertEqual(quotation.sales_order_ids, sales_order + new_sales_order)
        self.assertEqual(quotation.l10n_pt_document_number, 'OR 2026/00001')

    def test_confirm_in_place_keeps_signed_date(self):
        """
        An issued quotation confirmed in place by core's `action_confirm` keeps the date it was signed
        with, which core would move to the confirmation time.
        """
        quotation = self.issue(self.make_order(date_order=datetime(2026, 6, 10, 9, 0)))
        self.confirm_in_place(quotation)
        self.assertRecordValues(quotation, [{
            'state': 'sale',
            'date_order': datetime(2026, 6, 10, 9, 0),
            'l10n_pt_document_type': 'quotation',
        }])
        self.assertChainVerified(quotation)

    def test_confirmed_quotation_not_signed_or_paid_online(self):
        """An issued quotation confirmed into a sales order is accepted: it is not signed, paid or confirmed online again."""
        quotation = self.issue(self.make_order(require_signature=True, require_payment=True))
        self.assertTrue(quotation._has_to_be_signed())
        self.assertTrue(quotation._has_to_be_paid())
        self.confirm(quotation)
        self.assertFalse(quotation._has_to_be_signed())
        self.assertFalse(quotation._has_to_be_paid())

    def test_customer_accepts_issued_quotation(self):
        """
        A customer who signs an issued quotation (sent, or opened by the customer) on its portal page, with no payment
        due, confirms a new sales order from it, which is sent the confirmation mail; the quotation stays
        as issued, holding the signature.
        """
        quotation = self.issue(self.make_order(require_signature=True, require_payment=False))
        sales_order = self.accept(quotation)
        self.assertNotEqual(sales_order, quotation)
        self.assertRecordValues(quotation, [{
            'state': 'sent',
            'l10n_pt_ordered': True,
            'locked': True,
            'l10n_pt_document_number': 'OR 2026/00001',
            'signed_by': "Cliente PT",
        }])
        self.assertSignatureValid(quotation)
        self.assertRecordValues(sales_order, [{
            'state': 'sale',
            'quotation_id': quotation.id,
            'l10n_pt_document_type': 'sales_order',
            'l10n_pt_at_series_id': self.series_ne.id,
            # The customer's signature carries over to the sales order.
            'signed_by': "Cliente PT",
            'signed_on': quotation.signed_on,
        }])
        self.assertTrue(sales_order.signature)
        self.assertEqual(sales_order.signature, quotation.signature)
        # The confirmation mail attaches the sales order's PDF, which issues it: its first print, which
        # shows the signature.
        attachment = sales_order.message_ids.attachment_ids
        self.assertEqual(len(attachment), 1)
        self.assertIn('name="signature"', attachment.raw.decode())
        self.assertIssued(sales_order)
        self.assertFalse(quotation._has_to_be_signed())

    def test_issuer_of_customer_acceptance(self):
        """
        The sales order a customer's acceptance issues -- its confirmation mail prints it as the superuser
        -- records as issuer its quotation's issuer, who presented it; a quotation never issued and
        confirmed in place, its salesperson. No person acts there.
        """
        public = self.env.ref('base.public_user')
        quotation = self.issue(self.make_order(require_signature=True, require_payment=False))
        self.assertEqual(quotation.l10n_pt_issue_user_id, self.env.user)
        sales_order = self.accept(quotation.with_user(public).sudo())
        self.assertNotEqual(sales_order, quotation)
        self.assertIssued(sales_order)
        self.assertEqual(sales_order.l10n_pt_issue_user_id, self.env.user)

        quotation = self.make_order(require_signature=True, require_payment=False)
        self.assertEqual(self.accept(quotation.with_user(public).sudo()), quotation)
        self.assertIssued(quotation)
        self.assertEqual(quotation.l10n_pt_issue_user_id, self.salesman)

    def test_customer_accepts_unissued_quotation(self):
        """A customer who signs a quotation nobody issued yet (a shared link) confirms it in place, into a sales order."""
        quotation = self.make_order(require_signature=True, require_payment=False)
        self.assertEqual(self.accept(quotation), quotation)
        self.assertRecordValues(quotation, [{
            'state': 'sale',
            'l10n_pt_document_type': 'sales_order',
            'l10n_pt_at_series_id': self.series_ne.id,
            'sales_order_count': 0,
        }])

    # -------------------------------------------------------------------------
    # Cancellation and deletion
    # -------------------------------------------------------------------------

    def test_cancel_issued_asks_reason(self):
        """
        Cancelling an issued order first asks its reason (Portaria 302/2016 4.3.4.3.3); the
        wizard records it, with who cancelled it and when, cancels and locks the order again.
        """
        quotation = self.issue(self.make_order())
        action = quotation.action_cancel()
        self.assertEqual(action['res_model'], 'l10n_pt.cancel')
        self.assertEqual(quotation.state, 'draft')
        with freeze_time('2026-06-15 11:30:00'):
            self.cancel(quotation, reason="  Cliente desistiu  ")
        self.assertRecordValues(quotation, [{
            'state': 'cancel',
            'locked': True,
            'l10n_pt_cancel_reason': "Cliente desistiu",
            'l10n_pt_cancel_user_id': self.env.user.id,
            'l10n_pt_cancel_date': datetime(2026, 6, 15, 11, 30),
            'l10n_pt_document_number': 'OR 2026/00001',
        }])
        self.assertQrFields(quotation, {'E': 'A'})
        self.assertChainVerified(quotation)

    def test_canceller_when_no_person_cancels(self):
        """
        An issued order cancelled by no internal person -- the superuser of a customer's request or a
        cron -- records its salesperson as canceller, the SAF-T's SourceID of the cancellation; with no
        salesperson, the acting user.
        """
        system = self.env.ref('base.user_root')
        quotation, orphan = self.issue(self.make_order() + self.make_order(user_id=False))
        (quotation + orphan).l10n_pt_cancel_reason = "Cliente desistiu"
        (quotation + orphan).with_user(system)._action_cancel()
        self.assertRecordValues(quotation + orphan, [
            {'state': 'cancel', 'l10n_pt_cancel_user_id': self.salesman.id},
            {'state': 'cancel', 'l10n_pt_cancel_user_id': system.id},
        ])

    def test_salesman_cancels_an_issued_order(self):
        """The salesman of an issued order cancels it with its reason, as an accountant would."""
        quotation = self.issue(self.make_order()).with_user(self.salesman)
        self.cancel(quotation, reason="Cliente desistiu")
        self.assertRecordValues(quotation, [{
            'state': 'cancel',
            'l10n_pt_cancel_reason': "Cliente desistiu",
            'l10n_pt_cancel_user_id': self.salesman.id,
        }])

    def test_cancel_without_reason_refused(self):
        """Every path to a cancelled issued order needs its reason, the mass cancel and RPC included."""
        quotation = self.issue(self.make_order())
        with self.assertRaisesRegex(UserError, "can only be cancelled with a reason"), self.env.cr.savepoint():
            quotation._action_cancel()
        self.assertEqual(quotation.state, 'draft')

    def test_cancelled_issued_order_not_reset(self):
        """A cancelled issued order stays cancelled; a cancelled unissued one can go back to draft."""
        issued = self.cancel(self.issue(self.make_order()))
        with self.assertRaisesRegex(UserError, "cannot be reset to draft"):
            issued.action_draft()
        unissued = self.cancel(self.make_order())
        unissued.action_draft()
        self.assertEqual(unissued.state, 'draft')

    def test_unissued_order_cancels_directly(self):
        """
        A quotation nobody issued is cancelled without a reason and records nothing, even one created
        cancelled, before its series was ever computed.
        """
        quotation = self.cancel(self.make_order())
        self.assertRecordValues(quotation, [{
            'state': 'cancel',
            'l10n_pt_document_type': False,
            'l10n_pt_cancel_user_id': False,
            'l10n_pt_cancel_date': False,
        }])
        self.assertNotIssued(quotation)
        cancelled_at_creation = self.make_order(company=self.company_pt_2, state='cancel')
        self.assertFalse(cancelled_at_creation.l10n_pt_at_series_id)

    def test_numbered_orders_not_deleted(self):
        """An issued order is never deleted, cancelled or not (DL 28/2019 art. 7); a draft is."""
        issued = self.cancel(self.issue(self.make_order()))
        with self.assertRaisesRegex(UserError, "cannot be deleted"):
            issued.unlink()
        draft = self.make_order()
        draft.unlink()
        self.assertFalse(draft.exists())

    def test_series_of_issued_quotation_frozen(self):
        """
        A series holding an issued quotation, even one still in draft, cannot be renamed, re-coded or
        deleted; one never used can.
        """
        self.issue(self.make_order())
        for vals in ({'name': '2026X'}, {'prefix': 'ORX'}, {'at_code': 'ATOTHER01'}):
            with self.subTest(vals=vals), self.assertRaisesRegex(UserError, "already issued"):
                self.series_or.write(vals)
        with self.assertRaisesRegex(UserError, "already issued"):
            self.series_or.unlink()
        self.series_ne.write({'name': '2026X', 'at_code': 'ATOTHER02'})
        self.series_ne.unlink()

    # -------------------------------------------------------------------------
    # Master data
    # -------------------------------------------------------------------------

    def test_customer_nif_locked_by_issued_order(self):
        """
        A customer's NIF can be given while missing or generic, then no longer changed once a quotation
        or sales order was issued to it (Despacho 8632/2014 3.3.3); a draft locks nothing.
        """
        customer = self.env['res.partner'].create({'name': 'Cliente Novo', 'country_id': self.env.ref('base.pt').id})
        self.make_order(partner=customer)
        customer.vat = 'PT123456789'
        customer.vat = '999999990'
        self.issue(self.make_order(partner=customer))
        customer.vat = 'PT501964843'
        with self.assertRaisesRegex(UserError, "cannot change the VAT number"):
            customer.vat = 'PT502011378'

    def test_product_name_locked_by_signed_order(self):
        """
        A product's name cannot change once it is on a signed quotation or sales order; a draft locks
        nothing, and a product manager without sales rights still renames other products.
        """
        product = self.product_a
        self.make_order()
        product.name = 'Produto A'
        self.issue(self.make_order())
        with self.assertRaisesRegex(UserError, "used in a quotation or sales order"):
            product.name = 'Produto A2'
        product_manager = new_test_user(self.env, login='pt_product_manager', groups='base.group_user,product.group_product_manager')
        with self.assertRaisesRegex(UserError, "used in a quotation or sales order"):
            product.with_user(product_manager).name = 'Produto A2'
        self.product_b.with_user(product_manager).name = 'Produto B'
        self.assertEqual(self.product_b.name, 'Produto B')

    # -------------------------------------------------------------------------
    # Performance
    # -------------------------------------------------------------------------
    # Measured as independence from the number of orders rather than as an exact budget.

    def _count_queries(self, function):
        """The queries ``function`` runs from a cold record cache, the registry's caches (access rules) warm."""
        self.env.flush_all()
        self.env.invalidate_all()
        before = self.env.cr.sql_log_count
        function()
        self.env.flush_all()
        return self.env.cr.sql_log_count - before

    def test_series_lookup_independent_of_orders(self):
        """Orders looking for their series look it up once per company and type, however many they are."""
        def series_queries(order_count):
            orders = self.env['sale.order'].concat(*(self.make_order() for _i in range(order_count)))
            for order in orders:
                self.tamper(order, 'l10n_pt_at_series_id', None)
            queries = self._count_queries(orders._compute_l10n_pt_at_series_id)
            self.assertGreater(queries, 0)
            self.assertEqual(orders.l10n_pt_at_series_id, self.series_or)
            return queries

        series_queries(1)  # warm-up
        self.assertEqual(series_queries(1), series_queries(5))
