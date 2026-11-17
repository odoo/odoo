# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import TransactionCase, tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSePartnerCompany(TransactionCase):

    def test_sni_display_name(self):
        """SNI codes are shown as SCB writes them: 01.110."""
        sni = self.env['l10n_se.sni'].search([('code', '=', '01110')], limit=1)
        self.assertTrue(sni)
        self.assertTrue(sni.display_name.startswith('01.110 '))

    def test_primary_sni_follows_company(self):
        """Contacts get the primary SNI code of their company."""
        sni = self.env['l10n_se.sni'].search([], limit=2)
        company = self.env['res.partner'].create({
            'name': 'SNI AB',
            'is_company': True,
            'country_id': self.env.ref('base.se').id,
            'l10n_se_sni_ids': [(0, 0, {'sni_id': sni[1].id, 'sequence': 1}), (0, 0, {'sni_id': sni[0].id, 'sequence': 2})],
        })
        contact = self.env['res.partner'].create({'name': 'Kontakt', 'parent_id': company.id})
        self.assertEqual(company.l10n_se_primary_sni_id, sni[1])
        self.assertEqual(contact.l10n_se_primary_sni_id, sni[1])

    def test_f_tax_setting(self):
        """The F-tax approval is a company setting, off by default."""
        company = self.env['res.company'].create({'name': 'F-skatt AB', 'country_id': self.env.ref('base.se').id})
        self.assertFalse(company.l10n_se_f_tax_approved)
        settings = self.env['res.config.settings'].with_company(company).create({'l10n_se_f_tax_approved': True})
        settings.execute()
        self.assertTrue(company.l10n_se_f_tax_approved)
