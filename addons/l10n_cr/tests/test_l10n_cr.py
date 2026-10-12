from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nCr(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('cr')
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_a.country_id = cls.env.ref('base.cr')

    def test_document_types_number_independently(self):
        invoice = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[100.0], post=True)
        context = {'active_model': 'account.move', 'active_ids': invoice.ids}
        reversal = self.env['account.move.reversal'].with_context(context).create({'journal_id': invoice.journal_id.id})
        credit_note = self.env['account.move'].browse(reversal.refund_moves()['res_id'])
        debit_note = self.env['account.move'].browse(
            self.env['account.debit.note'].with_context(context).create({'copy_lines': True}).create_debit()['res_id'],
        )
        (credit_note | debit_note).action_post()
        self.assertEqual(
            (invoice | credit_note | debit_note).mapped('name'),
            ['FE 00000001', 'NC 00000001', 'ND 00000001'],
        )

    def test_district_onchange_fills_canton_and_province(self):
        san_rafael = self.env.ref('l10n_cr.district_cr_20108')
        with Form(self.env['res.partner']) as partner_form:
            partner_form.name = 'Coyol'
            partner_form.country_id = self.env.ref('base.cr')
            partner_form.l10n_cr_district_id = san_rafael
            self.assertEqual(partner_form.city_id, self.env.ref('l10n_cr.city_cr_201'))
            self.assertEqual(partner_form.state_id, self.env.ref('base.state_A'))
            partner_form.city_id = self.env.ref('l10n_cr.city_cr_101')
            self.assertFalse(partner_form.l10n_cr_district_id)
        self.assertEqual(san_rafael.display_name, 'San Rafael (Alajuela)')
        partner = self.env['res.partner'].create({'name': 'Coyol', 'country_id': self.env.ref('base.cr').id, 'l10n_cr_district_id': san_rafael.id})
        with Form(partner) as partner_form:
            partner_form.city_id = self.env.ref('l10n_cr.city_cr_201')
            partner_form.state_id = self.env.ref('base.state_SJ')
            self.assertFalse(partner_form.city_id)
            self.assertFalse(partner_form.l10n_cr_district_id)
            self.assertEqual(partner_form.state_id, self.env.ref('base.state_SJ'))
