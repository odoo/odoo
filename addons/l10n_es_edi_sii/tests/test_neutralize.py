# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import tagged, TransactionCase


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nEsEdiNeutralize(TransactionCase):

    def test_l10n_es_edi_neutralize(self):
        ar_company = self.env['res.company'].create({
            'name': 'Test ES Company',
            'l10n_es_edi_test_env': False,
        })

        self.env['res.company']._neutralize()
        self.assertEqual(ar_company.l10n_es_edi_test_env, True)
