import unittest

from psycopg2.errors import NotNullViolation

from odoo.exceptions import UserError, ValidationError
from odoo.tests import new_test_user, tagged
from odoo.tools import mute_logger

from odoo.addons.l10n_pt_certification import _post_init_hook
from odoo.addons.l10n_pt_certification.models.account_tax import L10N_PT_TAX_EXEMPTION_MENTIONS
from odoo.addons.l10n_pt_certification.tests.common import TestL10nPtCommon

# AT's table of VAT exemption reasons, v4.0 (2026-06-18).
AT_EXEMPTION_CODES_V4 = {
    'M01', 'M02', 'M04', 'M05', 'M06', 'M07', 'M09', 'M10', 'M11', 'M12', 'M13', 'M14', 'M15', 'M16',
    'M19', 'M20', 'M21', 'M25', 'M26', 'M30', 'M31', 'M32', 'M33', 'M34', 'M35', 'M40', 'M41', 'M42',
    'M43', 'M44', 'M45', 'M46', 'M99',
}


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtMasterData(TestL10nPtCommon):
    """
    What a PT document prints and exports about its customer, products and taxes cannot be rewritten
    once a document carries it (Despacho 8632/2014 3.3.3, 3.3.4; Portaria 302/2016 2.2, 2.4).
    Installing the module completes the PT companies that exist already; a PT company created later
    gets it all.
    """

    # -------------------------------------------------------------------------
    # Master data
    # -------------------------------------------------------------------------

    def test_customer_nif_locked(self):
        """
        Once a document was issued to a customer, its NIF can only be filled in when it was empty or
        generic; it cannot be changed or cleared, nor through one of its contacts (PT-41).
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
        """A customer without NIF to whom a document was issued keeps its name, until it is given a NIF (PT-41)."""
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

    def test_product_name_lock_whatever_the_user_reads(self):
        """
        The product-name lock checks every PT document using the product, whatever the user may read
        (PT-124): an accountant without sales, stock or PoS rights renames an unused product, and a
        product on another company's document stays locked with only this company active.
        """
        unused = self.env['product.product'].create({'name': 'Parafuso Inox'})
        unused.name = 'Parafuso Inox M8'
        self.assertEqual(unused.name, 'Parafuso Inox M8')
        used_elsewhere = self.env['product.product'].create({'name': 'Porca Inox'})
        self.series_factory(company_id=self.company_pt_2.id)
        self.post(self.make_invoice(company=self.company_pt_2, lines=[{'product_id': used_elsewhere}]))
        with self.assertRaisesRegex(UserError, "cannot modify the name of a product that has been used"):
            used_elsewhere.with_context(allowed_company_ids=self.company_pt.ids).name = 'Porca'

    def test_exemption_reasons(self):
        """
        The exemption reasons are AT's table v4.0, each mention fitting the SAF-T's 60 characters (PT-88);
        a PT tax charging nothing needs one, also when it becomes 0 % (PT-89).
        """
        self.assertEqual(set(L10N_PT_TAX_EXEMPTION_MENTIONS), AT_EXEMPTION_CODES_V4)
        self.assertEqual({code for code, _label in self.env['account.tax']._fields['l10n_pt_tax_exemption_reason'].selection}, AT_EXEMPTION_CODES_V4)
        self.assertFalse({code: mention for code, mention in L10N_PT_TAX_EXEMPTION_MENTIONS.items() if len(mention) > 60})
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
        3.1.1, PT-91); one's own password, non-PT users and the superuser are not concerned.
        """
        admin = new_test_user(
            self.env, login='pt_admin', groups='base.group_system,base.group_user', company_id=self.company_pt.id,
            company_ids=[(6, 0, (self.company_pt + self.company_foreign).ids)],
        )
        foreign_user = new_test_user(self.env, login='us_user', company_id=self.company_foreign.id, company_ids=[(6, 0, self.company_foreign.ids)])
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

    def test_new_company_chart(self):
        """A new PT company's chart carries the certification's data: exemption reasons, tax regions and categories."""
        company = self.setup_other_company(name='company_pt_3', vat='PT501964843')['company']
        ChartTemplate = self.env['account.chart.template'].with_company(company)
        self.assertEqual(ChartTemplate.ref('iva_pt_sale_isenta_art9').l10n_pt_tax_exemption_reason, 'M07')
        self.assertEqual(ChartTemplate.ref('iva_pt_sale_eu_isenta').l10n_pt_tax_exemption_reason, 'M16')
        self.assertRecordValues(ChartTemplate.ref('iva_pt_ac_sale_normal').tax_group_id, [{'l10n_pt_tax_region': 'PT-AC', 'l10n_pt_tax_category': 'N'}])

    def test_post_init_hook(self):
        """
        Installed on a database with PT companies, the module gives their taxes the exemption reasons,
        regions and categories. (Its sales-receipt group step is a no-op on 19.0: core dropped
        `account.group_sale_receipts`.)
        """
        exempt = self.env['account.chart.template'].with_company(self.company_pt_2).ref('iva_pt_sale_isenta')
        self.tamper(exempt, 'l10n_pt_tax_exemption_reason', None)
        self.tamper(exempt.tax_group_id, 'l10n_pt_tax_category', None)
        _post_init_hook(self.env)
        self.assertEqual(exempt.l10n_pt_tax_exemption_reason, 'M10')
        self.assertEqual(exempt.tax_group_id.l10n_pt_tax_category, 'E')

    def test_demo_data_for_several_companies(self):
        """The demo data of several PT companies loads at once, each with its own demo series and AT codes (PT-117)."""
        companies = self.company_pt_2 + self.setup_other_company(name='company_pt_3', vat='PT501964843')['company']
        self.env['account.chart.template']._l10n_pt_post_load_demo_data(companies + self.company_foreign)
        series = self.env['l10n_pt.at.series'].search([('company_id', 'in', companies.ids)])
        self.assertEqual(series.company_id, companies)
        self.assertEqual(len(set(series.mapped('at_code'))), len(series))
        self.assertFalse(self.env['l10n_pt.at.series'].search([('company_id', '=', self.company_foreign.id)]))

    @unittest.skip("PT-117 side finding: loading the certification's tax data creates a nameless tax when the company's chart lacks one")
    @mute_logger('odoo.sql_db')
    def test_tax_data_on_older_chart(self):
        """Installing on a company whose PT chart predates a tax of the certification data completes it without failing."""
        ChartTemplate = self.env['account.chart.template'].with_company(self.company_pt_2)
        art9 = ChartTemplate.ref('iva_pt_sale_isenta_art9')
        self.env['ir.model.data'].search([('model', '=', 'account.tax'), ('res_id', '=', art9.id)]).unlink()
        art9.unlink()
        try:
            ChartTemplate._l10n_pt_load_certification_tax_data(self.company_pt_2)
        except NotNullViolation:
            self.fail("the certification tax data created a tax missing from the chart")
