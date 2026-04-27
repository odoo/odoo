from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountReportsModelo(TestAccountReportsCommon):

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

        cls.account_income = cls.env['account.account'].create({
            'account_type': 'income',
            'name': 'Account Income',
            'code': '121020',
            'reconcile': True,
        })

        cls.report = cls.env.ref('l10n_es_reports.mod_349')

    def test_mod349_rectifications(self):
        """
            Test the rectification part of modelo 349, if an in_refund/ot_refund is found in the period :
                - if the linked original invoice is in the same period or if there is no linked invoice -> "Invoices" section
                - if the linked original invoice is before the period -> "Refunds" section
        """
        options = self._generate_options(self.report, '2019-04-01', '2019-04-30')

        # 1) we create a move in april 2019
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': fields.Date.from_string('2019-04-05'),
            'invoice_date': fields.Date.from_string('2019-04-05'),
            'partner_id': self.partner_a.id,
            'l10n_es_reports_mod349_invoice_type': 'E',
            'line_ids': [
                Command.create({
                    'product_id': self.product.id,
                    'account_id': self.account_income.id,
                    'quantity': 4,
                    'price_unit': self.product.lst_price,
                    'tax_ids': [],
                }),
            ]
        })

        invoice.action_post()

        # 2) The move is not reversed yet, so it should appear in the "Invoices" section on the April 2019 report
        report_lines = self.report._get_lines(options)
        self.assertLinesValues(
            report_lines,
            [0,                                                                                                                                         1],
            [
                ('Summary',                                                                                                                            ''),
                ('Total number of intra-community operations',                                                                                          1),
                ('Total amount of intra-community operations',                                                                                        400),
                ('Total number of intra-community refund operations',                                                                                   0),
                ('Amount of intra-community refund operations',                                                                                         0),
                ('Invoices',                                                                                                                           ''),
                ('E. Intra-community sales',                                                                                                          400),
                ('A. Intra-community purchases subject to taxes',                                                                                       0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                                  0),
                ('S. Intra-community sales of services carried out by the declarant',                                                                   0),
                ('I. Intra-community purchases of services',                                                                                            0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                            0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                              0),
                ('R. Transfers of goods made under consignment sales contracts.',                                                                       0),
                ('D. Returns of goods previously sent from the TAI',                                                                                    0),
                ('C. Replacements of goods',                                                                                                            0),
                ('Refunds',                                                                                                                            ''),
                ('E. Intra-community sales refunds',                                                                                                    0),
                ('A. Intra-community purchases subject to taxes',                                                                                       0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                                  0),
                ('S. Intra-community sales of services carried out by the declarant',                                                                   0),
                ('I. Intra-community purchases of services',                                                                                            0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                            0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                              0),
                ('R. Rectifications of transfers of goods made under consignment sale contracts.',                                                      0),
                ('D. Rectifications of returned goods previously sent from the TAI',                                                                    0),
                ('C. Rectifications for replacement of goods',                                                                                          0),
            ],
            options
        )

        expected_lines = invoice.line_ids.filtered_domain([
            ('account_type', 'in', ('asset_receivable', 'liability_payable')),
            ('tax_line_id', '=', False),
        ])

        # In Mod349 the auditable lines corresponds to the amount of intra-community operations and refunds
        line_dict = dict(zip(self.report.line_ids, report_lines))
        for report_line_code, expected_lines in [
            ('aeat_mod_349_statistics_invoices_total_amount', expected_lines),
            ('aeat_mod_349_statistics_refunds_total_amount', False),
        ]:
            report_line = self.env['account.report.line'].search([('code', '=', report_line_code)])
            action_dict = self.report.action_audit_cell(options, self._get_audit_params_from_report_line(options, report_line, line_dict[report_line]))
            result_lines = self.env['account.move.line'].search(action_dict['domain'])
            if expected_lines:
                self.assertEqual(result_lines, expected_lines)
            else:
                self.assertFalse(result_lines)

        # 3) We reverse the move in May 2019
        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=invoice.ids).create({
            'date': fields.Date.from_string('2019-05-05'),
            'journal_id': self.company_data['default_journal_sale'].id,
        })
        reversal = move_reversal.reverse_moves()
        reversed_move = self.env['account.move'].browse(reversal['res_id'])
        # As we don't want to fully reverse the move, we only reverse 1 of the 4 products on the invoice_line
        reversed_move.invoice_line_ids.quantity = 1

        reversed_move.action_post()

        # 4) We change the report period to May 2019, as the rectifications must target a move in a previous period
        options = self._generate_options(self.report, '2019-05-01', '2019-05-31')

        # 5) Now, in the report of May 2019, the new balance of the move created in April 2019 is reported in the 'Refunds' section
        # The new balance is computed like this : invoice.residual_amount - reversed_move.amount_total
        report_lines = self.report._get_lines(options)
        self.assertLinesValues(
            report_lines,
            [0,                                                                                                                                         1],
            [
                ('Summary',                                                                                                                            ''),
                ('Total number of intra-community operations',                                                                                          0),
                ('Total amount of intra-community operations',                                                                                          0),
                ('Total number of intra-community refund operations',                                                                                   1),
                ('Amount of intra-community refund operations',                                                                                    300.00),
                ('Invoices',                                                                                                                           ''),
                ('E. Intra-community sales',                                                                                                            0),
                ('A. Intra-community purchases subject to taxes',                                                                                       0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                                  0),
                ('S. Intra-community sales of services carried out by the declarant',                                                                   0),
                ('I. Intra-community purchases of services',                                                                                            0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                            0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                              0),
                ('R. Transfers of goods made under consignment sales contracts.',                                                                       0),
                ('D. Returns of goods previously sent from the TAI',                                                                                    0),
                ('C. Replacements of goods',                                                                                                            0),
                ('Refunds',                                                                                                                            ''),
                ('E. Intra-community sales refunds',                                                                                               300.00),
                ('A. Intra-community purchases subject to taxes',                                                                                       0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                                  0),
                ('S. Intra-community sales of services carried out by the declarant',                                                                   0),
                ('I. Intra-community purchases of services',                                                                                            0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                            0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                              0),
                ('R. Rectifications of transfers of goods made under consignment sale contracts.',                                                      0),
                ('D. Rectifications of returned goods previously sent from the TAI',                                                                    0),
                ('C. Rectifications for replacement of goods',                                                                                          0),
            ],
            options
        )
        expected_lines = reversed_move.line_ids.filtered_domain([
            ('account_type', 'in', ('asset_receivable', 'liability_payable')),
            ('tax_line_id', '=', False),
        ])

        # In Mod349 the auditable lines corresponds to the amount of intra-community operations and refunds
        line_dict = dict(zip(self.report.line_ids, report_lines))
        for report_line_code, expected_lines in [
            ('aeat_mod_349_statistics_invoices_total_amount', False),
            ('aeat_mod_349_statistics_refunds_total_amount', expected_lines),
        ]:
            report_line = self.env['account.report.line'].search([('code', '=', report_line_code)])
            action_dict = self.report.action_audit_cell(options, self._get_audit_params_from_report_line(options, report_line, line_dict[report_line]))
            result_lines = self.env['account.move.line'].search(action_dict['domain'])
            if expected_lines:
                self.assertEqual(result_lines, expected_lines)
            else:
                self.assertFalse(result_lines)

    def test_mod349_report_change_key_on_existing_move(self):
        """ This test makes sure the report display the lines depending on the key set on the move, even if we change
            the key of an existing move.
        """
        options = self._generate_options(self.report, fields.Date.from_string('2019-04-01'), fields.Date.from_string('2019-04-30'))

        # 1) We create an invoice with the key 'E'
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': fields.Date.from_string('2019-04-05'),
            'invoice_date': fields.Date.from_string('2019-04-05'),
            'partner_id': self.partner_a.id,
            'l10n_es_reports_mod349_invoice_type': 'E',
            'line_ids': [
                Command.create({
                    'product_id': self.product.id,
                    'account_id': self.account_income.id,
                    'quantity': 4,
                    'price_unit': self.product.lst_price,
                    'tax_ids': [],
                }),
            ]
        })

        invoice.action_post()

        # 2) We make sure the report show the value in the 'E' line
        self.assertLinesValues(
            self.report._get_lines(options),
            [0,                                                                                                                                   1],
            [
                ('Summary',                                                                                                                      ''),
                ('Total number of intra-community operations',                                                                                    1),
                ('Total amount of intra-community operations',                                                                               400.00),
                ('Total number of intra-community refund operations',                                                                             0),
                ('Amount of intra-community refund operations',                                                                                   0),
                ('Invoices',                                                                                                                     ''),
                ('E. Intra-community sales',                                                                                                 400.00),
                ('A. Intra-community purchases subject to taxes',                                                                                 0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                            0),
                ('S. Intra-community sales of services carried out by the declarant',                                                             0),
                ('I. Intra-community purchases of services',                                                                                      0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                      0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                        0),
                ('R. Transfers of goods made under consignment sales contracts.',                                                                 0),
                ('D. Returns of goods previously sent from the TAI',                                                                              0),
                ('C. Replacements of goods',                                                                                                      0),
                ('Refunds',                                                                                                                      ''),
                ('E. Intra-community sales refunds',                                                                                              0),
                ('A. Intra-community purchases subject to taxes',                                                                                 0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                            0),
                ('S. Intra-community sales of services carried out by the declarant',                                                             0),
                ('I. Intra-community purchases of services',                                                                                      0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                      0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                        0),
                ('R. Rectifications of transfers of goods made under consignment sale contracts.',                                                0),
                ('D. Rectifications of returned goods previously sent from the TAI',                                                              0),
                ('C. Rectifications for replacement of goods',                                                                                    0),
            ],
            options
        )

        # 3) We change the key of the invoice to set it to 'R'
        invoice.update({
            'state': 'draft',
            'l10n_es_reports_mod349_invoice_type': 'R',
        })
        invoice.action_post()

        # 4) The report should now put the value in the 'R' line
        self.assertLinesValues(
            self.report._get_lines(options),
            [0,                                                                                                                                             1],
            [
                ('Summary',                                                                                                                                ''),
                ('Total number of intra-community operations',                                                                                              1),
                ('Total amount of intra-community operations',                                                                                         400.00),
                ('Total number of intra-community refund operations',                                                                                       0),
                ('Amount of intra-community refund operations',                                                                                             0),
                ('Invoices',                                                                                                                               ''),
                ('E. Intra-community sales',                                                                                                                0),
                ('A. Intra-community purchases subject to taxes',                                                                                           0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                                      0),
                ('S. Intra-community sales of services carried out by the declarant',                                                                       0),
                ('I. Intra-community purchases of services',                                                                                                0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                                0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                                  0),
                ('R. Transfers of goods made under consignment sales contracts.',                                                                      400.00),
                ('D. Returns of goods previously sent from the TAI',                                                                                        0),
                ('C. Replacements of goods',                                                                                                                0),
                ('Refunds',                                                                                                                                ''),
                ('E. Intra-community sales refunds',                                                                                                        0),
                ('A. Intra-community purchases subject to taxes',                                                                                           0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                                      0),
                ('S. Intra-community sales of services carried out by the declarant',                                                                       0),
                ('I. Intra-community purchases of services',                                                                                                0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                                0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                                  0),
                ('R. Rectifications of transfers of goods made under consignment sale contracts.',                                                          0),
                ('D. Rectifications of returned goods previously sent from the TAI',                                                                        0),
                ('C. Rectifications for replacement of goods',                                                                                              0),
            ],
            options
        )

    def test_mod349_credit_note(self):
        """
            Test the rectification part of modelo 349, if an refund is found without linked invoice
            it still ends up in the "Rectificaciones" section.
        """
        options = self._generate_options(self.report, fields.Date.from_string('2019-04-01'), fields.Date.from_string('2019-04-30'))

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': fields.Date.from_string('2019-03-05'),
            'invoice_date': fields.Date.from_string('2019-03-05'),
            'partner_id': self.partner_a.id,
            'l10n_es_reports_mod349_invoice_type': 'E',
            'line_ids': [
                Command.create({
                    'product_id': self.product.id,
                    'account_id': self.account_income.id,
                    'quantity': 4,
                    'price_unit': self.product.lst_price,
                    'tax_ids': [],
                }),
            ]
        })

        invoice.action_post()

        credit_note = invoice._reverse_moves()

        credit_note.write({
            'date': fields.Date.from_string('2019-04-05'),
            'invoice_date': fields.Date.from_string('2019-04-05'),
        })

        credit_note.action_post()
        (invoice.line_ids | credit_note.line_ids).filtered(lambda l: l.display_type == 'payment_term').remove_move_reconcile()

        self.assertLinesValues(
            self.report._get_lines(options),
            [0,                                                                                                                                                     1],
            [
                ('Summary',                                                                                                                                ''),
                ('Total number of intra-community operations',                                                                                              0),
                ('Total amount of intra-community operations',                                                                                              0),
                ('Total number of intra-community refund operations',                                                                                       1),
                ('Amount of intra-community refund operations',                                                                                             0),
                ('Invoices',                                                                                                                               ''),
                ('E. Intra-community sales',                                                                                                                0),
                ('A. Intra-community purchases subject to taxes',                                                                                           0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                                      0),
                ('S. Intra-community sales of services carried out by the declarant',                                                                       0),
                ('I. Intra-community purchases of services',                                                                                                0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                                0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                                  0),
                ('R. Transfers of goods made under consignment sales contracts.',                                                                           0),
                ('D. Returns of goods previously sent from the TAI',                                                                                        0),
                ('C. Replacements of goods',                                                                                                                0),
                ('Refunds',                                                                                                                                ''),
                ('E. Intra-community sales refunds',                                                                                                        0),
                ('A. Intra-community purchases subject to taxes',                                                                                           0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                                      0),
                ('S. Intra-community sales of services carried out by the declarant',                                                                       0),
                ('I. Intra-community purchases of services',                                                                                                0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                                0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                                  0),
                ('R. Rectifications of transfers of goods made under consignment sale contracts.',                                                          0),
                ('D. Rectifications of returned goods previously sent from the TAI',                                                                        0),
                ('C. Rectifications for replacement of goods',                                                                                              0),
            ],
            options
        )

    def test_mod349_report_invoice_paid(self):
        """ This test makes sure the report numbers are correct after registering as paid an existing move.
        """
        options = self._generate_options(self.report, fields.Date.from_string('2019-04-01'), fields.Date.from_string('2019-04-30'))

        # 1) We create an invoice with the key 'E'
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': fields.Date.from_string('2019-04-05'),
            'invoice_date': fields.Date.from_string('2019-04-05'),
            'partner_id': self.partner_a.id,
            'l10n_es_reports_mod349_invoice_type': 'E',
            'line_ids': [
                Command.create({
                    'product_id': self.product.id,
                    'account_id': self.account_income.id,
                    'quantity': 4,
                    'price_unit': self.product.lst_price,
                    'tax_ids': [],
                }),
            ]
        })

        invoice.action_post()

        # 2) We make sure the report show the value in the 'E' line
        self.assertLinesValues(
            self.report._get_lines(options),
            [0,                                                                                                                                   1],
            [
                ('Summary',                                                                                                                      ''),
                ('Total number of intra-community operations',                                                                                    1),
                ('Total amount of intra-community operations',                                                                               400.00),
                ('Total number of intra-community refund operations',                                                                             0),
                ('Amount of intra-community refund operations',                                                                                   0),
                ('Invoices',                                                                                                                     ''),
                ('E. Intra-community sales',                                                                                                 400.00),
                ('A. Intra-community purchases subject to taxes',                                                                                 0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                            0),
                ('S. Intra-community sales of services carried out by the declarant',                                                             0),
                ('I. Intra-community purchases of services',                                                                                      0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                      0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                        0),
                ('R. Transfers of goods made under consignment sales contracts.',                                                                 0),
                ('D. Returns of goods previously sent from the TAI',                                                                              0),
                ('C. Replacements of goods',                                                                                                      0),
                ('Refunds',                                                                                                                      ''),
                ('E. Intra-community sales refunds',                                                                                              0),
                ('A. Intra-community purchases subject to taxes',                                                                                 0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                            0),
                ('S. Intra-community sales of services carried out by the declarant',                                                             0),
                ('I. Intra-community purchases of services',                                                                                      0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                      0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                        0),
                ('R. Rectifications of transfers of goods made under consignment sale contracts.',                                                0),
                ('D. Rectifications of returned goods previously sent from the TAI',                                                              0),
                ('C. Rectifications for replacement of goods',                                                                                    0),
            ],
            options
        )

        # 3) We register payment for the invoice
        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'payment_date': invoice.date,
        })._create_payments()

        # 4) We make sure the report show the same values
        self.assertLinesValues(
            self.report._get_lines(options),
            [0,                                                                                                                                   1],
            [
                ('Summary',                                                                                                                      ''),
                ('Total number of intra-community operations',                                                                                    1),
                ('Total amount of intra-community operations',                                                                               400.00),
                ('Total number of intra-community refund operations',                                                                             0),
                ('Amount of intra-community refund operations',                                                                                   0),
                ('Invoices',                                                                                                                     ''),
                ('E. Intra-community sales',                                                                                                 400.00),
                ('A. Intra-community purchases subject to taxes',                                                                                 0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                            0),
                ('S. Intra-community sales of services carried out by the declarant',                                                             0),
                ('I. Intra-community purchases of services',                                                                                      0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                      0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                        0),
                ('R. Transfers of goods made under consignment sales contracts.',                                                                 0),
                ('D. Returns of goods previously sent from the TAI',                                                                              0),
                ('C. Replacements of goods',                                                                                                      0),
                ('Refunds',                                                                                                                      ''),
                ('E. Intra-community sales refunds',                                                                                              0),
                ('A. Intra-community purchases subject to taxes',                                                                                 0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                            0),
                ('S. Intra-community sales of services carried out by the declarant',                                                             0),
                ('I. Intra-community purchases of services',                                                                                      0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                      0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                        0),
                ('R. Rectifications of transfers of goods made under consignment sale contracts.',                                                0),
                ('D. Rectifications of returned goods previously sent from the TAI',                                                              0),
                ('C. Rectifications for replacement of goods',                                                                                    0),
            ],
            options
        )

    def test_mod349_report_operators(self):
        """ This test makes sure the report show the number of partners involved in intra-community operations
        """
        options = self._generate_options(self.report, '2019-04-01', '2019-04-30')
        partner_b = self.env['res.partner'].create({
            'name': 'Test',
            'company_id': self.company_data['company'].id,
            'company_type': 'company',
            'country_id': self.company_data['company'].country_id.id,
        })


        # 1) We create several invoices with the key 'E'
        for partner_id in (self.partner_a | partner_b).ids * 2:
            invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'date': '2019-04-05',
                'invoice_date': '2019-04-05',
                'partner_id': partner_id,
                'l10n_es_reports_mod349_invoice_type': 'E',
                'line_ids': [
                    Command.create({
                        'product_id': self.product.id,
                        'account_id': self.account_income.id,
                        'quantity': 1,
                        'price_unit': self.product.lst_price,
                        'tax_ids': [],
                    }),
                ]
            })
            invoice.action_post()

        credit_note = invoice._reverse_moves()
        credit_note.write({
            'date': '2019-04-05',
            'invoice_date': '2019-04-05',
        })

        credit_note.action_post()

        # 2) We make sure the report show the value number of different partners in line 1 & 3 of the report
        self.assertLinesValues(
            self.report._get_lines(options),
            [0,                                                                                                                                   1],
            [
                ('Summary',                                                                                                                      ''),
                ('Total number of intra-community operations',                                                                                    2),
                ('Total amount of intra-community operations',                                                                               300.00),
                ('Total number of intra-community refund operations',                                                                             0),
                ('Amount of intra-community refund operations',                                                                                   0),
                ('Invoices',                                                                                                                     ''),
                ('E. Intra-community sales',                                                                                                 300.00),
                ('A. Intra-community purchases subject to taxes',                                                                                 0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                            0),
                ('S. Intra-community sales of services carried out by the declarant',                                                             0),
                ('I. Intra-community purchases of services',                                                                                      0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                      0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                        0),
                ('R. Transfers of goods made under consignment sales contracts.',                                                                 0),
                ('D. Returns of goods previously sent from the TAI',                                                                              0),
                ('C. Replacements of goods',                                                                                                      0),
                ('Refunds',                                                                                                                      ''),
                ('E. Intra-community sales refunds',                                                                                              0),
                ('A. Intra-community purchases subject to taxes',                                                                                 0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                            0),
                ('S. Intra-community sales of services carried out by the declarant',                                                             0),
                ('I. Intra-community purchases of services',                                                                                      0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                      0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                        0),
                ('R. Rectifications of transfers of goods made under consignment sale contracts.',                                                0),
                ('D. Rectifications of returned goods previously sent from the TAI',                                                              0),
                ('C. Rectifications for replacement of goods',                                                                                    0),
            ],
            options
        )

    def test_mod349_report_no_invoice_type(self):
        """ This test makes sure the report show the number of partners involved in intra-community operations
            with mod349 invoice type set
        """
        options = self._generate_options(self.report, '2019-04-01', '2019-04-30')
        # 1) We create intra-community invoice with no mod349 key
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-04-05',
            'invoice_date': '2019-04-05',
            'partner_id': self.partner_a.id,
            'line_ids': [
                Command.create({
                    'product_id': self.product.id,
                    'account_id': self.account_income.id,
                    'quantity': 1,
                    'price_unit': self.product.lst_price,
                    'tax_ids': [],
                }),
            ]
        })
        invoice.l10n_es_reports_mod349_invoice_type = False
        invoice.action_post()

        # 2) We make sure the report does not show the invoice

        self.assertLinesValues(
            self.report._get_lines(options),
            [0,                                                                                                                                   1],
            [
                ('Summary',                                                                                                                      ''),
                ('Total number of intra-community operations',                                                                                    0),
                ('Total amount of intra-community operations',                                                                                    0),
                ('Total number of intra-community refund operations',                                                                             0),
                ('Amount of intra-community refund operations',                                                                                   0),
                ('Invoices',                                                                                                                     ''),
                ('E. Intra-community sales',                                                                                                      0),
                ('A. Intra-community purchases subject to taxes',                                                                                 0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                            0),
                ('S. Intra-community sales of services carried out by the declarant',                                                             0),
                ('I. Intra-community purchases of services',                                                                                      0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                      0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                        0),
                ('R. Transfers of goods made under consignment sales contracts.',                                                                 0),
                ('D. Returns of goods previously sent from the TAI',                                                                              0),
                ('C. Replacements of goods',                                                                                                      0),
                ('Refunds',                                                                                                                      ''),
                ('E. Intra-community sales refunds',                                                                                              0),
                ('A. Intra-community purchases subject to taxes',                                                                                 0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                            0),
                ('S. Intra-community sales of services carried out by the declarant',                                                             0),
                ('I. Intra-community purchases of services',                                                                                      0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                      0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                        0),
                ('R. Rectifications of transfers of goods made under consignment sale contracts.',                                                0),
                ('D. Rectifications of returned goods previously sent from the TAI',                                                              0),
                ('C. Rectifications for replacement of goods',                                                                                    0),
            ],
            options
        )

    def test_mod349_report_multi_installment_payment_terms(self):
        """ This test makes sure the report show the correct amount when the invoice is paid using
            multi installment payment terms (30% Now, Balance 60 Days)
        """
        options = self._generate_options(self.report, '2019-04-01', '2019-04-30')
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-04-05',
            'invoice_date': '2019-04-05',
            'partner_id': self.partner_a.id,
            'invoice_payment_term_id': self.pay_terms_b.id,
            'line_ids': [
                Command.create({
                    'product_id': self.product.id,
                    'quantity': 1,
                    'price_unit': self.product.lst_price,
                    'tax_ids': [],
                }),
            ]
        })
        invoice.action_post()

        self.assertLinesValues(
            self.report._get_lines(options),
            [0,                                                                                                                                   1],
            [
                ('Summary',                                                                                                                      ''),
                ('Total number of intra-community operations',                                                                                    1),
                ('Total amount of intra-community operations',                                                                                100.0),
                ('Total number of intra-community refund operations',                                                                             0),
                ('Amount of intra-community refund operations',                                                                                   0),
                ('Invoices',                                                                                                                     ''),
                ('E. Intra-community sales',                                                                                                  100.0),
                ('A. Intra-community purchases subject to taxes',                                                                                 0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                            0),
                ('S. Intra-community sales of services carried out by the declarant',                                                             0),
                ('I. Intra-community purchases of services',                                                                                      0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                      0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                        0),
                ('R. Transfers of goods made under consignment sales contracts.',                                                                 0),
                ('D. Returns of goods previously sent from the TAI',                                                                              0),
                ('C. Replacements of goods',                                                                                                      0),
                ('Refunds',                                                                                                                      ''),
                ('E. Intra-community sales refunds',                                                                                              0),
                ('A. Intra-community purchases subject to taxes',                                                                                 0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                            0),
                ('S. Intra-community sales of services carried out by the declarant',                                                             0),
                ('I. Intra-community purchases of services',                                                                                      0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                      0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                        0),
                ('R. Rectifications of transfers of goods made under consignment sale contracts.',                                                0),
                ('D. Rectifications of returned goods previously sent from the TAI',                                                              0),
                ('C. Rectifications for replacement of goods',                                                                                    0),
            ],
            options
        )

    def test_mod349_report_multi_currency(self):
        """ This test makes sure the report show the correct amount when invoicing in a foreign currency
        """
        options = self._generate_options(self.report, '2019-04-01', '2019-04-30')
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-04-05',
            'invoice_date': '2019-04-05',
            'partner_id': self.partner_a.id,
            'invoice_payment_term_id': self.pay_terms_b.id,
            'currency_id': self.other_currency.id,
            'line_ids': [
                Command.create({
                    'product_id': self.product.id,
                    'quantity': 1,
                    'price_unit': self.product.lst_price,
                    'tax_ids': [],
                }),
            ]
        })
        invoice.action_post()

        self.assertLinesValues(
            self.report._get_lines(options),
            [0,                                                                                                                                   1],
            [
                ('Summary',                                                                                                                      ''),
                ('Total number of intra-community operations',                                                                                    1),
                ('Total amount of intra-community operations',                                                                                 50.0),
                ('Total number of intra-community refund operations',                                                                             0),
                ('Amount of intra-community refund operations',                                                                                   0),
                ('Invoices',                                                                                                                     ''),
                ('E. Intra-community sales',                                                                                                   50.0),
                ('A. Intra-community purchases subject to taxes',                                                                                 0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                            0),
                ('S. Intra-community sales of services carried out by the declarant',                                                             0),
                ('I. Intra-community purchases of services',                                                                                      0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                      0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                        0),
                ('R. Transfers of goods made under consignment sales contracts.',                                                                 0),
                ('D. Returns of goods previously sent from the TAI',                                                                              0),
                ('C. Replacements of goods',                                                                                                      0),
                ('Refunds',                                                                                                                      ''),
                ('E. Intra-community sales refunds',                                                                                              0),
                ('A. Intra-community purchases subject to taxes',                                                                                 0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                            0),
                ('S. Intra-community sales of services carried out by the declarant',                                                             0),
                ('I. Intra-community purchases of services',                                                                                      0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                      0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                        0),
                ('R. Rectifications of transfers of goods made under consignment sale contracts.',                                                0),
                ('D. Rectifications of returned goods previously sent from the TAI',                                                              0),
                ('C. Rectifications for replacement of goods',                                                                                    0),
            ],
            options
        )

    def test_mod349_invoice_date(self):
        """
            Test the rectification part of modelo 349, if an in_refund/out_refund is found in the period defined by the move date
        """
        options = self._generate_options(self.report, '2020-01-01', '2020-01-30')

        # We create an invoice with invoice date in 2019 and accounting date 2020
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2019-12-31',
            'date': '2020-01-01',
            'partner_id': self.partner_a.id,
            'l10n_es_reports_mod349_invoice_type': 'E',
            'line_ids': [
                Command.create({
                    'product_id': self.product.id,
                    'account_id': self.account_income.id,
                    'quantity': 4,
                    'price_unit': self.product.lst_price,
                }),
            ]
        })

        invoice.action_post()

        # We reverse the move in 2020
        move_reversal = self.env['account.move.reversal'].with_context(
            active_model="account.move",
            active_ids=invoice.ids,
        ).create({
            'date': fields.Date.from_string('2020-01-02'),
            'journal_id': self.company_data['default_journal_sale'].id,
        })
        reversal = move_reversal.reverse_moves()
        reversed_move = self.env['account.move'].browse(reversal['res_id'])
        reversed_move.action_post()

        # In the report of Jan 2020, the new balance of the move created in 2019 should be nulled by the credit note because
        # its accounting date is 2020
        report_lines = self.report._get_lines(options)
        self.assertLinesValues(
            report_lines,
            [0,                                                                                                                                                     1],
            [
                ('Summary',                                                                                                                      ''),
                ('Total number of intra-community operations',                                                                                    1),
                ('Total amount of intra-community operations',                                                                                    0),
                ('Total number of intra-community refund operations',                                                                             0),
                ('Amount of intra-community refund operations',                                                                                   0),
                ('Invoices',                                                                                                                     ''),
                ('E. Intra-community sales',                                                                                                      0),
                ('A. Intra-community purchases subject to taxes',                                                                                 0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                            0),
                ('S. Intra-community sales of services carried out by the declarant',                                                             0),
                ('I. Intra-community purchases of services',                                                                                      0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                      0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                        0),
                ('R. Transfers of goods made under consignment sales contracts.',                                                                 0),
                ('D. Returns of goods previously sent from the TAI',                                                                              0),
                ('C. Replacements of goods',                                                                                                      0),
                ('Refunds',                                                                                                                      ''),
                ('E. Intra-community sales refunds',                                                                                              0),
                ('A. Intra-community purchases subject to taxes',                                                                                 0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                            0),
                ('S. Intra-community sales of services carried out by the declarant',                                                             0),
                ('I. Intra-community purchases of services',                                                                                      0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                      0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                        0),
                ('R. Rectifications of transfers of goods made under consignment sale contracts.',                                                0),
                ('D. Rectifications of returned goods previously sent from the TAI',                                                              0),
                ('C. Rectifications for replacement of goods',                                                                                    0),
            ],
            options
        )

        expected_lines = (invoice | reversed_move).line_ids.filtered_domain([
            ('account_type', 'in', ('asset_receivable', 'liability_payable')),
            ('tax_line_id', '=', False),
        ])

        # In Mod349 the auditable lines corresponds to the amount of intra-community operations and refunds
        line_dict = dict(zip(self.report.line_ids, report_lines))
        for report_line_code, expected_lines in [
            ('aeat_mod_349_statistics_invoices_total_amount', expected_lines),
            ('aeat_mod_349_statistics_refunds_total_amount', False),
        ]:
            report_line = self.env['account.report.line'].search([('code', '=', report_line_code)])
            action_dict = self.report.action_audit_cell(options, self._get_audit_params_from_report_line(options, report_line, line_dict[report_line]))
            result_lines = self.env['account.move.line'].search(action_dict['domain'])
            if expected_lines:
                self.assertEqual(result_lines, expected_lines)
            else:
                self.assertFalse(result_lines)

    def test_mod349_report_line_audit(self):
        """ This test makes sure the report shows the correct results for the auditable lines
        """
        options = self._generate_options(self.report, '2019-04-01', '2019-04-30')
        invoices = self.env['account.move']
        for key in ('E', 'R', 'E'):
            invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'date': '2019-04-05',
                'invoice_date': '2019-04-05',
                'partner_id': self.partner_a.id,
                'line_ids': [
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': 1,
                        'price_unit': self.product.lst_price,
                        'tax_ids': [],
                    }),
                ]
            })
            invoice.update({
                'l10n_es_reports_mod349_invoice_type': key,
            })
            invoice.action_post()
            invoices |= invoice

        # We reverse the last move
        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=invoice.ids).create({
            'date': '2019-04-06',
            'journal_id': self.company_data['default_journal_sale'].id,
        })
        reversal = move_reversal.reverse_moves()
        reversed_move = self.env['account.move'].browse(reversal['res_id'])
        reversed_move.action_post()

        # The report show values in 'E' and 'R' lines
        report_lines = self.report._get_lines(options)
        self.assertLinesValues(
            report_lines,
            [0,                                                                                                                                                     1],
            [
                ('Summary',                                                                                                                      ''),
                ('Total number of intra-community operations',                                                                                    1),
                ('Total amount of intra-community operations',                                                                               200.00),
                ('Total number of intra-community refund operations',                                                                             0),
                ('Amount of intra-community refund operations',                                                                                   0),
                ('Invoices',                                                                                                                     ''),
                ('E. Intra-community sales',                                                                                                 100.00),
                ('A. Intra-community purchases subject to taxes',                                                                                 0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                            0),
                ('S. Intra-community sales of services carried out by the declarant',                                                             0),
                ('I. Intra-community purchases of services',                                                                                      0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                      0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                        0),
                ('R. Transfers of goods made under consignment sales contracts.',                                                            100.00),
                ('D. Returns of goods previously sent from the TAI',                                                                              0),
                ('C. Replacements of goods',                                                                                                      0),
                ('Refunds',                                                                                                                      ''),
                ('E. Intra-community sales refunds',                                                                                              0),
                ('A. Intra-community purchases subject to taxes',                                                                                 0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                            0),
                ('S. Intra-community sales of services carried out by the declarant',                                                             0),
                ('I. Intra-community purchases of services',                                                                                      0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                      0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                        0),
                ('R. Rectifications of transfers of goods made under consignment sale contracts.',                                                0),
                ('D. Rectifications of returned goods previously sent from the TAI',                                                              0),
                ('C. Rectifications for replacement of goods',                                                                                    0),
            ],
            options
        )

        expected_lines = (invoices | reversed_move).line_ids.filtered_domain([
            ('account_type', 'in', ('asset_receivable', 'liability_payable')),
            ('tax_line_id', '=', False),
        ])

        # In Mod349 the auditable lines corresponds to the amount of intra-community operations and refunds
        line_dict = dict(zip(self.report.line_ids, report_lines))
        for report_line_code, expected_lines in [
            ('aeat_mod_349_statistics_invoices_total_amount', expected_lines),
            ('aeat_mod_349_statistics_refunds_total_amount', False),
        ]:
            report_line = self.env['account.report.line'].search([('code', '=', report_line_code)])
            action_dict = self.report.action_audit_cell(options, self._get_audit_params_from_report_line(options, report_line, line_dict[report_line]))
            result_lines = self.env['account.move.line'].search(action_dict['domain'])
            if expected_lines:
                self.assertEqual(result_lines, expected_lines)
            else:
                self.assertFalse(result_lines)
