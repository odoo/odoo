from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountReportsModelo130(TestAccountReportsCommon):

    @classmethod
    @TestAccountReportsCommon.setup_country('es')
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].country_id = cls.env.ref('base.be').id
        cls.company_data['company'].currency_id = cls.env.ref('base.EUR').id
        cls.company_data['currency'] = cls.env.ref('base.EUR')

        cls.partner_a = cls.env['res.partner'].create({
            'name': 'Bidule',
            'company_id': cls.company_data['company'].id,
            'company_type': 'company',
            'country_id': cls.company_data['company'].country_id.id,
        })

        cls.product = cls.env['product.product'].create({
            'name': 'Crazy Product',
            'lst_price': 100.0
        })

        cls.report = cls.env.ref('l10n_es_modelo130.mod_130')

    def test_mod130_filter_date(self):
        """Test mod130 will compute from the beginning of fiscalyear
        """
        options = self._generate_options(self.report, '2019-04-01', '2019-04-30')

        # 1) we create a move in january 2019
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': fields.Date.from_string('2019-01-01'),
            'invoice_date': fields.Date.from_string('2019-01-01'),
            'partner_id': self.partner_a.id,
            'line_ids': [
                Command.create({
                    'product_id': self.product.id,
                    'quantity': 4,
                    'price_unit': self.product.lst_price,
                }),
            ]
        })

        invoice.action_post()

        # 2) The move is created in this fiscalyear, so it should appear in Mod130 when we select up to 2019-04-30
        self.assertLinesValues(
            self.report._get_lines(options),
            [0,                                                                                                                                                           1],
            [
               ('I. Economic activities in the direct assessment system, normal or simplified mode, other than agriculture, livestock farming, forestry and fishing.',   ''),
               ('[01] Revenue',                                                                                                                                      400.00),
               ('[02] Supplies',                                                                                                                                       0.00),
               ('[03] Box 01 - Box 02',                                                                                                                              400.00),
               ('[04] 20% (or custom %) applied on Box 03',                                                                                                           80.00),
               ('[05] Residual amounts of past quarters',                                                                                                              0.00),
               ('[06] Sum of withholding\'s',                                                                                                                          0.00),
               ('[07] Box 04 - Box 05 - Box 06',                                                                                                                      80.00),
               ('II. Agriculture, livestock farming, forestry and fishing in the direct assessment system, normal or simplified mode.',                                  ''),
               ('[08] Revenue',                                                                                                                                        0.00),
               ('[09] 2% (or custom %) applied on Box 08',                                                                                                             0.00),
               ('[10] Sum of withholding\'s',                                                                                                                          0.00),
               ('[11] Box 09 - Box 10',                                                                                                                                0.00),
               ('III. Total settlement.',                                                                                                                                ''),
               ('[12] Box 07 + Box 11',                                                                                                                               80.00),
               ('[13] Value of the reduction based on sum of net earnings from the previous tax year',                                                                 0.00),
               ('[14] Box 12 - Box 13',                                                                                                                               80.00),
               ('[15] Negative amount of previous self-assessments',                                                                                                   0.00),
               ('[16] Deduction for allocating amounts to the payment of loans for the acquisition or rehabilitation',                                                 0.00),
               ('[17] Box 14 - Box 15 - Box 16',                                                                                                                      80.00),
               ('[18] Complementary declaration',                                                                                                                      0.00),
               ('[19] Box 17 - Box 18',                                                                                                                               80.00),
            ],
            options
        )
