import unittest
from datetime import date
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import RedirectWarning
from odoo.tests import freeze_time, tagged

from odoo.addons.l10n_pt_certification.const import PT_CERTIFICATION_NUMBER
from odoo.addons.l10n_pt_certification.models.account_tax import L10N_PT_TAX_EXEMPTION_PRINTED_REASONS
from odoo.addons.l10n_pt_pos.tests.common import TestL10nPtPosCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtPosConfig(TestL10nPtPosCommon):
    """
    Opening a PT Point of Sale checks, before any sale, what every document it issues needs: products
    with a reference and a tax (SAF-T ProductCode, Portaria 302/2016 4.1.4.19.13), payment methods
    with an AT payment mechanism (4.1.4.19.17), and AT series holding a validation code for each
    document type it issues (Portaria 195/2020 art. 3). The PoS provides its series itself: a cashier
    can neither create nor register one (D-3, amended for the PoS).
    """

    def _loja_journal(self):
        """A second sales journal of ``company_pt``, without any series."""
        return self.env['account.journal'].create({
            'name': 'Vendas Loja',
            'code': 'LOJ',
            'type': 'sale',
            'company_id': self.company_pt.id,
        })

    def _pos_series(self, journal):
        return self.env['l10n_pt.at.series'].search([('journal_id', '=', journal.id)], order='prefix')

    # -------------------------------------------------------------------------
    # Opening
    # -------------------------------------------------------------------------

    def test_opens(self):
        """A PoS with its series, products and payment methods in order opens, for the cashier."""
        session = self.open_session()
        self.assertEqual(session.state, 'opened')

    @unittest.skip("PT-139 (todo): the check compares product categories with PoS categories, so it never finds a product")
    def test_product_without_tax_refused(self):
        """
        A product the PoS sells without a tax of its company refuses the opening, naming it, whether the
        PoS limits its categories or sells every product available in the PoS.
        """
        product = self._create_pos_product('Postal', 'POSTAL', 1.0, taxes_id=False)
        for limit_categories in (True, False):
            self.config.limit_categories = limit_categories
            with self.subTest(limit_categories=limit_categories), self.assertRaisesRegex(RedirectWarning, "one tax and an internal reference") as caught:
                self.open_session()
            self.assertEqual(caught.exception.args[1]['domain'], [('id', 'in', product.ids)])

    def test_payment_method_without_mechanism_refused(self):
        """A payment method without an AT payment mechanism refuses the opening, naming it."""
        method = self.env['pos.payment.method'].create({
            'name': 'Transferência',
            'journal_id': self.company_data['default_journal_bank'].id,
        })
        self.config.payment_method_ids = [Command.link(method.id)]
        with self.assertRaisesRegex(RedirectWarning, "should have a payment mechanism") as caught:
            self.open_session()
        self.assertEqual(caught.exception.args[1]['domain'], [('id', 'in', method.ids)])

    def test_non_pt_pos_not_checked(self):
        """A Point of Sale of another country is opened without the PT checks."""
        company = self.company_foreign
        method = self.env['pos.payment.method'].with_company(company).create({
            'name': 'Cash US',
            'journal_id': self.company_data_foreign['default_journal_cash'].id,
            'company_id': company.id,
        })
        self.assertFalse(method.l10n_pt_pos_payment_mechanism)
        config = self.env['pos.config'].with_company(company).create({
            'name': 'Shop US',
            'company_id': company.id,
            'invoice_journal_id': self.company_data_foreign['default_journal_sale'].id,
            'payment_method_ids': [Command.set(method.ids)],
        })
        series_count = self.env['l10n_pt.at.series'].search_count([])
        config.open_ui()
        self.assertTrue(config.current_session_id)
        self.assertEqual(self.env['l10n_pt.at.series'].search_count([]), series_count)

    # -------------------------------------------------------------------------
    # AT series
    # -------------------------------------------------------------------------

    def test_existing_series_used(self):
        """
        The series the PoS needs are those of its invoice journal for FT, FR, FS and NC, valid today;
        existing ones are used, none is created. They are handed back without superuser rights.
        """
        series_count = self.env['l10n_pt.at.series'].search_count([])
        series = self.config.with_user(self.cashier)._l10n_pt_pos_ensure_at_series()
        self.assertEqual(series, self.series_ft + self.series_fr + self.series_fs + self.series_nc)
        self.assertFalse(series.env.su)
        self.assertEqual(series.env.uid, self.cashier.id)
        self.open_session()
        self.assertEqual(self.env['l10n_pt.at.series'].search_count([]), series_count)

    def test_missing_series_created_offline_refused(self):
        """
        Missing series are created when the PoS is opened, even by a cashier. Without the AT
        webservice they have no validation code: the opening is refused, naming them, for a manager to
        enter their codes; the series are kept, created in their own transaction (PT-53, which test mode
        cannot show: every cursor is the test's). With their codes the PoS opens.
        """
        journal = self._loja_journal()
        self.config.invoice_journal_id = journal
        with self.enter_registry_test_mode():
            try:
                self.open_session()
            except RedirectWarning as e:
                refusal = e
            else:
                self.fail("A PoS whose series have no AT code was opened")
        # Named and prefixed as the series form proposes: after the journal, its name taken by the
        # company's '2026' series of the same types.
        series = self._pos_series(journal)
        self.assertRecordValues(series, [
            {'name': 'LOJ2026', 'prefix': 'LOJ', 'document_type': 'out_invoice', 'at_code': False},
            {'name': 'LOJ2026', 'prefix': 'RECLOJ', 'document_type': 'out_invoice_receipt', 'at_code': False},
            {'name': 'LOJ2026', 'prefix': 'RLOJ', 'document_type': 'out_refund', 'at_code': False},
            {'name': 'LOJ2026', 'prefix': 'SLOJ', 'document_type': 'out_receipt', 'at_code': False},
        ])
        for record in series:
            self.assertIn(record.document_identifier, refusal.args[0])
        self.assertEqual(set(refusal.args[1]['domain'][0][2]), set(series.ids))

        for record in series:
            record.at_code = f'AT{record.prefix}'
        with self.enter_registry_test_mode():
            session = self.open_session()
        self.assertEqual(session.state, 'opened')
        self.assertEqual(self._pos_series(journal), series)
        order = self.sell(session=session)
        self.assertEqual(order.account_move.name, 'SLOJ LOJ2026/00001')

    def test_missing_series_registered_with_at(self):
        """With the AT webservice configured, the series created on opening are registered and the PoS opens."""
        def register(series):
            series.at_code = f'ATREG{series.prefix}'

        journal = self._loja_journal()
        self.config.invoice_journal_id = journal
        self.company_pt.sudo().write({'l10n_pt_at_ws_env': 'test', 'l10n_pt_at_ws_username': '123456789/1'})
        with (
            patch.object(self.registry['l10n_pt.at.series'], 'action_register_at_series', register),
            self.enter_registry_test_mode(),
        ):
            session = self.open_session()
        self.assertEqual(session.state, 'opened')
        self.assertEqual(self._pos_series(journal).mapped('at_code'), ['ATREGLOJ', 'ATREGRECLOJ', 'ATREGRLOJ', 'ATREGSLOJ'])

    def test_series_of_next_year_created_at_sync(self):
        """
        A session opened on 31 December sells into the next year: the series of the order's date are
        provided as it is synced. Without their codes the sale is refused (PT-22); with them it is issued.
        """
        with freeze_time('2026-12-31 18:00:00'):
            session = self.open_session()
        with freeze_time('2027-01-01 00:30:00'):
            with (
                self.enter_registry_test_mode(),
                self.assertRaisesRegex(RedirectWarning, "SINV 2027 has no AT validation code"),
                self.env.cr.savepoint(),
            ):
                self.sell(session=session)
            with self.enter_registry_test_mode():
                series_2027 = self.config._l10n_pt_pos_ensure_at_series(date(2027, 1, 1))
            self.assertRecordValues(series_2027, [
                {'name': '2027', 'prefix': 'INV', 'document_type': 'out_invoice'},
                {'name': '2027', 'prefix': 'RECINV', 'document_type': 'out_invoice_receipt'},
                {'name': '2027', 'prefix': 'SINV', 'document_type': 'out_receipt'},
                {'name': '2027', 'prefix': 'RINV', 'document_type': 'out_refund'},
            ])
            for record in series_2027:
                record.at_code = f'AT2027{record.prefix}'
            order = self.sell(session=session)
        self.assertEqual(order.account_move.name, 'SINV 2027/00001')

    # -------------------------------------------------------------------------
    # Payment mechanisms
    # -------------------------------------------------------------------------

    def test_payment_mechanism_defaults(self):
        """
        A PT cash method is paid in cash, 'NU'; a mechanism set by hand is kept, but not 'NU' once the
        method no longer counts cash (PT-86). A method of another country gets none.
        """
        self.assertEqual(self.cash_method.l10n_pt_pos_payment_mechanism, 'NU')
        self.assertEqual(self.card_method.l10n_pt_pos_payment_mechanism, 'CC')
        self.cash_method.l10n_pt_pos_payment_mechanism = 'CO'
        self.assertEqual(self.cash_method.l10n_pt_pos_payment_mechanism, 'CO')
        cash = self.env['pos.payment.method'].create({
            'name': 'Numerário 2',
            'journal_id': self.company_data['default_journal_cash'].id,
        })
        self.assertEqual(cash.l10n_pt_pos_payment_mechanism, 'NU')
        cash.journal_id = self.company_data['default_journal_bank']
        self.assertFalse(cash.l10n_pt_pos_payment_mechanism)

    # -------------------------------------------------------------------------
    # Loaded data
    # -------------------------------------------------------------------------

    def test_loaded_data(self):
        """
        A PT till loads the generic final consumer, the exemption mentions it prints, the taxes'
        exemption reasons and the software certification number it prints on every receipt.
        """
        session = self.open_session()
        self.assertIn((self.final_consumer.id,), self.config.get_limited_partners_loading())
        self.assertEqual(
            self.config._load_pos_data_read(self.config, self.config)[0]['_l10n_pt_final_consumer_id'],
            self.final_consumer.id,
        )
        self.assertEqual(
            session._load_pos_data_read(session, self.config)[0]['_l10n_pt_tax_exemption_reasons'],
            L10N_PT_TAX_EXEMPTION_PRINTED_REASONS,
        )
        self.assertIn('l10n_pt_tax_exemption_reason', self.env['account.tax']._load_pos_data_fields(self.config.id))
        self.assertEqual(
            self.env['pos.session'].l10n_pt_pos_get_software_info(self.company_pt.id, self.config.id),
            {'l10n_pt_pos_certification_number': PT_CERTIFICATION_NUMBER},
        )
