from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests import new_test_user, tagged

from odoo.addons.l10n_pt_certification import _post_init_hook
from odoo.addons.l10n_pt_certification.const import PT_QR_NOT_SUBJECT_EXEMPTION_REASONS
from odoo.addons.l10n_pt_certification.models.account_tax import L10N_PT_TAX_EXEMPTION_MENTIONS
from odoo.addons.l10n_pt_certification.tests.common import TestL10nPtCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtMasterData(TestL10nPtCommon):
    """
    What a PT document prints and exports about its customer, products and taxes cannot be rewritten
    once a document carries it (Despacho 8632/2014 3.3.3, 3.3.4; Portaria 302/2016 2.2, 2.4).
    Installing the module completes the PT companies that exist already; a PT company created later
    gets it all with its chart, as every class's set-up does.
    """

    # -------------------------------------------------------------------------
    # Master data
    # -------------------------------------------------------------------------

    def test_customer_nif_locked(self):
        """
        Once a document was issued to a customer, its NIF can only be filled in when it was empty or
        generic; it cannot be changed or cleared, nor through one of its contacts.
        """
        partner = self.env['res.partner'].create({'name': 'Cliente Genérico', 'vat': 'PT999999990', 'country_id': self.env.ref('base.pt').id})
        contact = self.env['res.partner'].create({'name': 'Contacto', 'parent_id': self.partner_pt.id, 'type': 'invoice'})
        self.issue(self.post(self.make_invoice(partner=partner) + self.make_invoice(partner=contact)))
        partner.vat = 'PT123456789'
        for record, vat in ((partner, 'PT501964843'), (partner, False), (self.partner_pt, 'PT500000000'), (self.partner_pt, False)):
            with self.subTest(partner=record.name, vat=vat), self.assertRaisesRegex(UserError, "change the VAT number of a partner that already has issued documents"):
                record.vat = vat
        self.partner_pt.vat = 'pt 501 964 843'
        untouched = self.env['res.partner'].create({'name': 'Sem documentos', 'vat': 'PT501964843'})
        untouched.vat = 'PT123456789'

    def test_customer_without_nif_name_locked(self):
        """A customer without NIF to whom a document was issued keeps its name, until it is given a NIF."""
        anonymous = self.env['res.partner'].create({'name': 'Cliente sem NIF'})
        generic = self.env['res.partner'].create({'name': 'Consumidor', 'vat': '999999990'})
        self.issue(self.post(self.make_invoice(partner=anonymous) + self.make_invoice(partner=generic)))
        for partner in (anonymous, generic):
            with self.subTest(partner=partner.name), self.assertRaisesRegex(UserError, "change the name of a partner without a VAT number"):
                partner.name = 'Outro nome'
        anonymous.write({'name': 'Cliente Identificado', 'vat': 'PT501964843'})
        self.partner_pt.name = 'Cliente PT Renomeado'

    def test_products(self):
        """
        A product name has two characters at least, and cannot change once on a posted PT invoice; every
        product gets an internal reference, the SAF-T's ProductCode.
        """
        with self.assertRaisesRegex(UserError, "at least 2 characters long"):
            self.env['product.product'].create({'name': 'A'})
        product = self.env['product.product'].create({'name': 'Parafuso Inox'})
        self.assertEqual(product.default_code, f'PARA_{product.id}')
        product.name = 'Parafuso Inox M8'
        self.post(self.make_invoice(lines=[{'product_id': product}]))
        with self.assertRaisesRegex(UserError, "cannot modify the name of a product that has been used"):
            product.name = 'Parafuso'
        with self.assertRaisesRegex(UserError, "at least 2 characters long"):
            self.product_service.name = 'S'

    def test_product_name_locked_by_annulled_invoice(self):
        """
        An annulled invoice keeps its lines in the SAF-T, product names included: it locks the name as
        a posted one does. A draft never numbered, then cancelled, is no document and locks nothing.
        """
        annulled = self.env['product.product'].create({'name': 'Parafuso Inox'})
        invoice = self.post(self.make_invoice(lines=[{'product_id': annulled}]))
        invoice.button_cancel()
        self.assertTrue(invoice.l10n_pt_document_number)
        with self.assertRaisesRegex(UserError, "cannot modify the name of a product that has been used"):
            annulled.name = 'Parafuso'
        discarded = self.env['product.product'].create({'name': 'Porca Inox'})
        self.make_invoice(lines=[{'product_id': discarded}]).button_cancel()
        discarded.name = 'Porca'

    def test_product_name_lock_whatever_the_user_reads(self):
        """
        The product-name lock checks every PT invoice using the product, whatever the user may read:
        an invoicing user who manages products, in this company only, renames an unused product, not
        one on another company's invoice. The sales, stock and PoS locks are tested in
        their modules.
        """
        product_user = new_test_user(
            self.env, login='pt_product_user',
            groups='base.group_user,account.group_account_invoice,product.group_product_manager',
            company_id=self.company_pt.id, company_ids=[Command.set(self.company_pt.ids)],
        )
        unused = self.env['product.product'].create({'name': 'Parafuso Inox'})
        unused.with_user(product_user).name = 'Parafuso Inox M8'
        self.assertEqual(unused.name, 'Parafuso Inox M8')
        used_elsewhere = self.env['product.product'].create({'name': 'Porca Inox'})
        self.series_factory(company_id=self.company_pt_2.id)
        self.post(self.make_invoice(company=self.company_pt_2, lines=[{'product_id': used_elsewhere}]))
        with self.assertRaisesRegex(UserError, "cannot modify the name of a product that has been used"):
            used_elsewhere.with_user(product_user).name = 'Porca'

    def test_exemption_reasons(self):
        """
        The exemption reasons are AT's table, whose version `account_tax.py` cites; the test checks what
        a revision of it could break rather than copying it. Each mention fits the SAF-T's
        TaxExemptionReason, 6 to 60 characters; the reasons the chart data and the QR code's
        `L:` rely on are in it; the PT chart's taxes carry the certification's values. A PT tax
        charging nothing needs a reason, also when it becomes 0 %.
        """
        self.assertFalse({code: mention for code, mention in L10N_PT_TAX_EXEMPTION_MENTIONS.items() if not 6 <= len(mention) <= 60})
        ChartTemplate = self.env['account.chart.template'].with_company(self.company_pt)
        chart_reasons = {vals.get('l10n_pt_tax_exemption_reason') for vals in ChartTemplate._get_pt_certification_account_tax().values()} - {'', None}
        self.assertTrue(chart_reasons)
        self.assertLessEqual(chart_reasons | set(PT_QR_NOT_SUBJECT_EXEMPTION_REASONS), set(L10N_PT_TAX_EXEMPTION_MENTIONS))
        self.assertEqual(ChartTemplate.ref('iva_pt_sale_isenta_art9').l10n_pt_tax_exemption_reason, 'M07')
        self.assertEqual(ChartTemplate.ref('iva_pt_sale_eu_isenta').l10n_pt_tax_exemption_reason, 'M16')
        self.assertRecordValues(ChartTemplate.ref('iva_pt_ac_sale_normal').tax_group_id, [{'l10n_pt_tax_region': 'PT-AC', 'l10n_pt_tax_category': 'N'}])
        with self.assertRaisesRegex(ValidationError, "Exempt taxes require an exemption reason"):
            self.env['account.tax'].create({'name': 'Isento', 'amount': 0.0, 'type_tax_use': 'sale'})
        tax = self.env['account.tax'].create({'name': 'Taxa 5%', 'amount': 5.0, 'type_tax_use': 'sale'})
        with self.assertRaisesRegex(ValidationError, "Exempt taxes require an exemption reason"):
            tax.amount = 0.0
        tax.write({'amount': 0.0, 'l10n_pt_tax_exemption_reason': 'M07'})
        with self.assertRaisesRegex(ValidationError, "Exempt taxes require an exemption reason"):
            tax.l10n_pt_tax_exemption_reason = False
        foreign_tax = self.env['account.tax'].with_company(self.company_foreign).create({
            'name': 'Exempt', 'amount': 0.0, 'type_tax_use': 'sale', 'company_id': self.company_foreign.id,
        })
        self.assertFalse(foreign_tax.l10n_pt_tax_exemption_reason)

    def test_pt_users_choose_their_password(self):
        """
        Nobody but a PT user may set its password, an administrator included (Despacho 8632/2014
        3.1.1); one's own password, non-PT users and the superuser are not concerned.
        """
        admin = new_test_user(
            self.env, login='pt_admin', groups='base.group_system,base.group_user', company_id=self.company_pt.id,
            company_ids=[Command.set((self.company_pt + self.company_foreign).ids)],
        )
        foreign_user = new_test_user(self.env, login='us_user', company_id=self.company_foreign.id, company_ids=[Command.set(self.company_foreign.ids)])
        with self.assertRaisesRegex(UserError, "users of a Portuguese company choose their own password"):
            self.billing_user.with_user(admin).write({'password': 'escolhida-pelo-admin'})
        wizard = self.env['change.password.wizard'].with_user(admin).with_context(active_model='res.users', active_ids=self.billing_user.ids).create({})
        wizard.user_ids.new_passwd = 'escolhida-pelo-admin'
        with self.assertRaisesRegex(UserError, "users of a Portuguese company choose their own password"):
            wizard.change_password_button()
        self.billing_user.with_user(self.billing_user).change_password('pt_billing_user', 'a-minha-palavra-passe')
        foreign_user.with_user(admin).write({'password': 'not-portuguese'})
        self.billing_user.sudo().write({'password': 'reposta-por-script'})

    def test_company_region(self):
        """A PT company's tax region follows its district: the Azores and Madeira have their own (Portaria 302/2016 2.1.2)."""
        for state, region in (('base.state_pt_pt-20', 'PT-AC'), ('base.state_pt_pt-30', 'PT-MA'), ('base.state_pt_pt-11', 'PT')):
            with self.subTest(region=region):
                self.company_pt.state_id = self.env.ref(state)
                self.assertEqual(self.company_pt.l10n_pt_region_code, region)

    # -------------------------------------------------------------------------
    # Installation
    # -------------------------------------------------------------------------

    def test_post_init_hook(self):
        """
        Installed on a database with PT companies, the module gives their taxes the exemption reasons,
        regions and categories, also when a chart lacks one of the taxes it certifies: deleted, or added
        to the PT chart after the chart was loaded. That tax is not created.
        """
        ChartTemplate = self.env['account.chart.template'].with_company(self.company_pt_2)
        ChartTemplate.ref('iva_pt_sale_isenta_art9').unlink()
        Tax = self.env['account.tax'].with_context(active_test=False)
        tax_count = Tax.search_count([('company_id', '=', self.company_pt_2.id)])
        exempt = ChartTemplate.ref('iva_pt_sale_isenta')
        self.tamper(exempt, 'l10n_pt_tax_exemption_reason', None)
        self.tamper(exempt.tax_group_id, 'l10n_pt_tax_category', None)
        # A failed install rolls back: so does this, or the test would end on a broken transaction.
        # The hook runs as the superuser, as an install does: it reaches every PT company, the test
        # user's or not.
        with self.env.cr.savepoint():
            _post_init_hook(self.env(su=True))
        self.assertEqual(exempt.l10n_pt_tax_exemption_reason, 'M10')
        self.assertEqual(exempt.tax_group_id.l10n_pt_tax_category, 'E')
        self.assertFalse(ChartTemplate.ref('iva_pt_sale_isenta_art9', raise_if_not_found=False))
        self.assertEqual(Tax.search_count([('company_id', '=', self.company_pt_2.id)]), tax_count)
