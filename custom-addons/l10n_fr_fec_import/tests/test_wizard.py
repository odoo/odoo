# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import logging

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo import tools

_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', 'post_install', '-at_install')
class AccountTestFecImport(AccountTestInvoicingCommon):
    """ Main test class for Account FEC import testing """

    # ----------------------------------------
    # 1:: Files repo
    # ----------------------------------------

    test_content = """
        JournalCode\tJournalLib\tEcritureNum\tEcritureDate\tCompteNum\tCompteLib\tCompAuxNum\tCompAuxLib\tPieceRef\tPieceDate\tEcritureLib\tDebit\tCredit\tEcritureLet\tDateLet\tValidDate\tMontantdevise\tIdevise
        ACH\tACHATS\tACH000001\t20180808\t62270000\tLegal costs and litigation\t\t\t1\t20180808\tADVANCE PAYMENT COMPANY FORMALITIES\t500,00\t0,00\t\t\t20190725\t\t
        ACH\tACHATS\tACH000001\t20180808\t44566000\tVat on other goods and services\t\t\t1\t20180808\tADVANCE PAYMENT COMPANY FORMALITIES\t100,00\t0,00\tAA\t\t20190725\t\t
        ACH\tACHATS\tACH000001\t20180808\t45500000\tAssociate's current account\t\t\t1\t20180808\tADVANCE PAYMENT COMPANY FORMALITIES\t0,00\t600,00\t\t\t20190725\t\t
        ACH\tACHATS\tACH000002\t20180808\t61320000\tPartner rentals 01\t\t\t2\t20180808\tDOMICILIATION\t300,00\t0,00\t\t\t20190725\t\t
        ACH\tACHATS\tACH000002\t20180808\t44566000\tVat on other goods and services\t\t\t2\t20180808\tDOMICILIATION\t60,00\t0,00\tAA\t\t20190725\t\t
        ACH\tACHATS\tACH000002\t20180808\t45500000\tAssociate's current account\t\t\t2\t20180808\tDOMICILIATION\t0,00\t360,00\t\t\t20190725\t\t
        ACH\tACHATS\tACH000003\t20180910\t61320000\tPartner rentals 01\t\t\t3\t20180910\tPARTNER 01\t41,50\t0,00\t\t\t20190725\t\t
        ACH\tACHATS\tACH000003\t20180910\t44566000\tVat on other goods and services\t\t\t3\t20180910\tPARTNER 01\t8,30\t0,00\tAA\t\t20190725\t\t
        ACH\tACHATS\tACH000003\t20180910\t40100000\tSuppliers\tPARTNER01\tPARTNER 01\t3\t20180910\tPARTNER 01\t0,00\t49,80\tAA\t\t20190725\t\t
        ACH\tACHATS\tACH000004\t20180910\t512001\tVat on other goods and services\t\t\t3\t20180910\tPARTNER 01\t49,80\t0,00\tAA\t\t20190725\t\t
        ACH\tACHATS\tACH000004\t20180910\t40100000\tSuppliers\tPARTNER01\tPARTNER 01\t3\t20180910\tPARTNER 01\t0,00\t49,80\tAA\t\t20190725\t\t
        ACH\tACHATS\tACH000005\t20180910\t5120010\tVat on other goods and services\t\t\t3\t20180910\tPARTNER 01\t49,80\t0,00\tAA\t\t20190725\t\t
        ACH\tACHATS\tACH000005\t20180910\t40100000\tSuppliers\tPARTNER01\tPARTNER 01\t3\t20180910\tPARTNER 01\t0,00\t49,80\tAA\t\t20190725\t\t
        ACH\tACHATS\tACH000006\t20180910\t61320000\tPRIMES D'ASSURANCES\t\t\t3\t20180910\tASSURANCE\t200,50\t0,00\t\t\t20190725\t\tEUR
        ACH\tACHATS\tACH000006\t20180910\t44566000\tASSURANCE\t\t\t3\t20180910\tASSURANCE\t0,00\t200,50\t\t\t20190725\t\tEUR
    """

    # ----------------------------------------
    # 2:: Test class body
    # ----------------------------------------

    @classmethod
    def setUpClass(cls, chart_template_ref='fr'):
        """ Setup all the prerequisite entities for the CSV import tests to run """

        super().setUpClass(chart_template_ref=chart_template_ref)

        # Company -------------------------------------
        cls.company = cls.company_data['company']
        cls.company_export = cls.company_data_2['company']
        cls.company_export.vat = 'FR15437982937'
        cls.company.account_fiscal_country_id = cls.env.ref('base.fr')

        # Wizard --------------------------------------
        cls.wizard = cls.env['account.fec.import.wizard'].create({'company_id': cls.company.id})
        cls._attach_file_to_wizard(cls, cls.test_content, cls.wizard)

        # Export records for import test --------------
        cls.moves = cls.env['account.move'].with_company(cls.company_export).create([{
            'company_id': cls.company_export.id,
            'name': 'INV/001/123456',
            'date': datetime.date(2010, 1, 1),
            'invoice_date': datetime.date(2010, 1, 1),
            'move_type': 'entry',
            'partner_id': cls.partner_a.id,
            'journal_id': cls.company_data_2['default_journal_sale'].id,
            'line_ids': [(0, 0, {
                'company_id': cls.company_export.id,
                'name': 'line-1',
                'account_id': cls.company_data_2['default_account_receivable'].id,
                'credit': 0.0,
                'debit': 100.30
            }), (0, 0, {
                'company_id': cls.company_export.id,
                'name': 'line-2',
                'account_id': cls.company_data_2['default_account_tax_sale'].id,
                'credit': 100.30,
                'debit': 0.0
            })],
        }, {
            'company_id': cls.company_export.id,
            'name': 'INV/001/123457',
            'move_type': 'entry',
            'date': datetime.date(2010, 1, 1),
            'invoice_date': datetime.date(2010, 1, 1),
            'partner_id': cls.partner_b.id,
            'journal_id': cls.company_data_2['default_journal_purchase'].id,
            'line_ids': [(0, 0, {
                'company_id': cls.company_export.id,
                'name': 'line-3',
                'account_id': cls.company_data_2['default_account_payable'].id,
                'credit': 65.15,
                'debit': 0.0,
            }), (0, 0, {
                'company_id': cls.company_export.id,
                'name': 'line-4',
                'account_id': cls.company_data_2['default_account_expense'].id,
                'credit': 0.0,
                'debit': 65.15,
            })],
        }])

        # Export Wizard ----------------------------------------
        cls.export_wizard = cls.env['account.fr.fec'].create([{
            'date_from': datetime.date(1990, 1, 1),
            'date_to': datetime.date.today(),
            'test_file': True,
            'export_type': 'nonofficial'
        }])

        # Imbalanced moves test content -----------------------

        # Start by splitting the content in matrices
        matrix = [line.lstrip().split('\t') for line in cls.test_content.lstrip().split('\n') if line.lstrip()]

        # To balance by day, change the move names to 9 different ones,
        # so that its name cannot be used as grouping key
        for idx, line in enumerate(matrix[1:]):
            line[2] = "move_%s" % idx

        def join_matrix(matrix):
            return "\n".join(["\t".join(line) for line in matrix])

        cls.test_content_imbalanced_day = join_matrix(matrix)

        # To balance by month, change the move date of 2 move lines out of 3 of the same original move
        # to another day, so that the day cannot be used as grouping key
        for line in matrix[3:6]:
            line[3] = "20180809"
        cls.test_content_imbalanced_month = join_matrix(matrix)

        # To make them unbalanceable, make one line belong to another month than any other line
        # so that the month cannot be used as grouping key
        matrix[6][3] = "20181010"
        cls.test_content_imbalanced_none = join_matrix(matrix)

    def _attach_file_to_wizard(self, content, wizard=None):
        """ Create an attachment and bind it to the wizard and its log """
        content = '\n'.join([line.strip(' ') for line in content.split('\n') if line])
        if wizard:
            wizard.attachment_id = base64.b64encode(content.encode('utf-8'))

    # ----------------------------------------
    # 3:: Test methods
    # ----------------------------------------

    def test_import_fec_accounts(self):
        """ Test that the account are correctly imported from the FEC file """

        self.wizard._import_files(['account.account'])

        account_codes = ('401000', '445660', '622700')
        domain = [('company_id', '=', self.company.id), ('code', 'in', account_codes)]
        accounts = self.env['account.account'].search(domain, order='code')

        expected_values = [{
            'name': 'Suppliers - Purchase of goods and services',
            'account_type': 'liability_payable',
            'reconcile': True
        }, {
            'name': 'Deductible VAT on other goods and services',
            'account_type': 'asset_current',
            'reconcile': False,
        }, {
            'name': 'Legal and litigation fees',
            'account_type': 'expense',
            'reconcile': False,
        }, ]
        self.assertRecordValues(accounts, expected_values)

    def test_import_fec_journals(self):
        """ Test that the journals are correctly imported from the FEC file """

        self.wizard._import_files(['account.account', 'account.journal'])

        journal_codes = ('ACH', )
        domain = [('company_id', '=', self.company.id), ('code', 'in', journal_codes)]
        journals = self.env['account.journal'].search(domain, order='code')

        expected_values = [{'name': 'FEC-ACHATS', 'type': 'general'}]
        self.assertRecordValues(journals, expected_values)

    def test_import_fec_partners(self):
        """ Test that the partners are correctly imported from the FEC file """

        self.wizard._import_files(['account.account', 'account.journal', 'res.partner'])

        partner_refs = ('PARTNER01', )
        domain = [('company_id', '=', self.company.id), ('ref', 'in', partner_refs)]
        partners = self.env['res.partner'].search(domain, order='ref')

        expected_values = [{'name': 'PARTNER 01'}]
        self.assertRecordValues(partners, expected_values)

    def test_import_fec_moves(self):
        """ Test that the moves are correctly imported from the FEC file """

        self.wizard._import_files(['account.account', 'account.journal', 'res.partner', 'account.move'])

        move_names = ('ACH000001', 'ACH000002', 'ACH000003')
        domain = [('company_id', '=', self.company.id), ('name', 'in', move_names)]
        moves = self.env['account.move'].search(domain, order='name')

        journal = self.env['account.journal'].with_context(active_test=False).search([('code', '=', 'ACH')])
        expected_values = [{
            'name': move_names[0],
            'journal_id': journal.id,
            'date': datetime.date(2018, 8, 8),
            'move_type': 'entry',
            'ref': '1'
        }, {
            'name': move_names[1],
            'journal_id': journal.id,
            'date': datetime.date(2018, 8, 8),
            'move_type': 'entry',
            'ref': '2'
        }, {
            'name': move_names[2],
            'journal_id': journal.id,
            'date': datetime.date(2018, 9, 10),
            'move_type': 'entry',
            'ref': '3'
        }]
        self.assertRecordValues(moves, expected_values)

        self.assertEqual(1, len(moves[2].line_ids.filtered(lambda x: x.partner_id.name == 'PARTNER 01')))

    def test_import_fec_move_lines(self):
        """ Test that the move_lines are correctly imported from the FEC file """

        self.wizard._import_files(['account.account', 'account.journal', 'res.partner', 'account.move'])

        move_names = ('ACH000001', 'ACH000002', 'ACH000003', 'ACH000006')
        domain = [('company_id', '=', self.company.id), ('move_name', 'in', move_names)]
        move_lines = self.env['account.move.line'].search(domain, order='move_name, id')
        columns = ['name', 'credit', 'debit']
        lines = [
            ('ADVANCE PAYMENT COMPANY FORMALITIES', 0.00, 500.00),
            ('ADVANCE PAYMENT COMPANY FORMALITIES', 0.00, 100.00),
            ('ADVANCE PAYMENT COMPANY FORMALITIES', 600.00, 0.00),
            ('DOMICILIATION', 0.00, 300.00),
            ('DOMICILIATION', 0.00, 60.00),
            ('DOMICILIATION', 360.00, 0.00),
            ('PARTNER 01', 0.00, 41.50),
            ('PARTNER 01', 0.00, 8.30),
            ('PARTNER 01', 49.80, 0.00),
            ('ASSURANCE', 0.00, 200.50),
            ('ASSURANCE', 200.50, 0.00),
        ]
        expected_values = [dict(zip(columns, line)) for line in lines]
        self.assertRecordValues(move_lines, expected_values)

    def test_import_fec_demo_file(self):
        """ Test that the demo FEC file is correctly imported """

        # Attach the demo file
        with tools.file_open('l10n_fr_fec_import/demo/123459254FEC20190430.txt', mode='rb') as test_file:
            content = test_file.read().decode('latin-1')
            self._attach_file_to_wizard(content, self.wizard)

        # Import the file
        last = self.env['account.move'].search([], order='id desc', limit=1)
        self.wizard._import_files(['account.account', 'account.journal', 'res.partner', 'account.move'])
        new = self.env['account.move'].search([('id', '>', last.id)])
        new.action_post()

        # Verify move_lines presence
        move_names = ('ACH000001', 'ACH000002', 'ACH000003')
        domain = [('company_id', '=', self.company.id), ('move_name', 'in', move_names)]
        move_lines = self.env['account.move.line'].search(domain, order='move_name, id')
        self.assertEqual(9, len(move_lines))

        # Verify Reconciliation
        domain = [('company_id', '=', self.company.id), ('reconciled', '=', True)]
        move_lines = self.env['account.move.line'].search(domain)
        self.assertEqual(256, len(move_lines))

        # Verify Full Reconciliation
        domain = [('company_id', '=', self.company.id), ('full_reconcile_id', '!=', False)]
        move_lines = self.env['account.move.line'].search(domain)
        self.assertEqual(256, len(move_lines))

        # Verify Journal types
        domain = [('company_id', '=', self.company.id), ('name', '=', 'FEC-BQ 552')]
        journal = self.env['account.journal'].search(domain)
        self.assertEqual(journal.type, 'bank')

    def test_import_fec_export(self):
        """ Test that imports the results of a FEC export """

        # Generate the FEC content with the export wizard
        self.export_wizard.sudo().with_company(self.company_export).generate_fec()
        content = self.export_wizard.fec_data
        self.wizard.attachment_id = content

        # Import the exported FEC file in the test's main company
        self.wizard._import_files(['account.account', 'account.journal', 'res.partner', 'account.move'])

        # Verify moves data
        new_moves = self.env['account.move'].search([
            ('company_id', '=', self.company_export.id),
            ('tax_closing_end_date', '=', False),  # exclude automatic tax closing  entries
        ], order="name")
        columns = ['company_id', 'name', 'journal_id', 'partner_id', 'date']
        moves_data = [
            (self.company_export.id, 'INV/001/123456', self.company_data_2['default_journal_sale'].id, self.partner_a.id, datetime.date(2010, 1, 1)),
            (self.company_export.id, 'INV/001/123457', self.company_data_2['default_journal_purchase'].id, self.partner_b.id, datetime.date(2010, 1, 1)),
        ]
        expected_values = [dict(zip(columns, move_data)) for move_data in moves_data]
        self.assertRecordValues(new_moves, expected_values)

        # Verify moves lines data
        columns = ['company_id', 'name', 'credit', 'debit', 'account_id']
        lines_data = [
            (self.company_export.id, 'line-1', 0.00, 100.30, self.company_data_2['default_account_receivable'].id),
            (self.company_export.id, 'line-2', 100.30, 0.00, self.company_data_2['default_account_tax_sale'].id),
            (self.company_export.id, 'line-3', 65.15, 0.00, self.company_data_2['default_account_payable'].id),
            (self.company_export.id, 'line-4', 0.00, 65.15, self.company_data_2['default_account_expense'].id),
        ]
        expected_values = [dict(zip(columns, line_data)) for line_data in lines_data]
        new_lines = new_moves.mapped("line_ids").sorted(key=lambda x: x.name)
        self.assertRecordValues(new_lines, expected_values)

    def test_balance_moves_by_day(self):
        """ Test that the imbalanced moves are correctly balanced with a grouping by day """

        self._attach_file_to_wizard(self.test_content_imbalanced_day, self.wizard)
        self.wizard._import_files(['account.account', 'account.journal', 'res.partner', 'account.move'])

        domain = [('company_id', '=', self.company.id), ('move_name', 'in', ('ACH/20180808', 'ACH/20180910'))]
        move_lines = self.env['account.move.line'].search(domain, order='move_name,name')

        self.assertEqual(
            move_lines.mapped(lambda line: (line.move_name, line.name)),
            [
                ('ACH/20180808', 'ADVANCE PAYMENT COMPANY FORMALITIES'),
                ('ACH/20180808', 'ADVANCE PAYMENT COMPANY FORMALITIES'),
                ('ACH/20180808', 'ADVANCE PAYMENT COMPANY FORMALITIES'),
                ('ACH/20180808', 'DOMICILIATION'),
                ('ACH/20180808', 'DOMICILIATION'),
                ('ACH/20180808', 'DOMICILIATION'),
                ('ACH/20180910', 'ASSURANCE'),
                ('ACH/20180910', 'ASSURANCE'),
                ('ACH/20180910', 'PARTNER 01'),
                ('ACH/20180910', 'PARTNER 01'),
                ('ACH/20180910', 'PARTNER 01'),
                ('ACH/20180910', 'PARTNER 01'),
                ('ACH/20180910', 'PARTNER 01'),
                ('ACH/20180910', 'PARTNER 01'),
                ('ACH/20180910', 'PARTNER 01'),
            ])

    def test_balance_moves_by_month(self):
        """ Test that the imbalanced moves are correctly balanced with a grouping by month """

        self._attach_file_to_wizard(self.test_content_imbalanced_month, self.wizard)
        self.wizard._import_files(['account.account', 'account.journal', 'res.partner', 'account.move'])

        domain = [('company_id', '=', self.company.id), ('move_name', 'in', ('ACH/201808', 'ACH/201809'))]
        move_lines = self.env['account.move.line'].search(domain, order='move_name,name')
        self.assertEqual(
            move_lines.mapped(lambda line: (line.move_name, line.name)),
            [
                ('ACH/201808', 'ADVANCE PAYMENT COMPANY FORMALITIES'),
                ('ACH/201808', 'ADVANCE PAYMENT COMPANY FORMALITIES'),
                ('ACH/201808', 'ADVANCE PAYMENT COMPANY FORMALITIES'),
                ('ACH/201808', 'DOMICILIATION'),
                ('ACH/201808', 'DOMICILIATION'),
                ('ACH/201808', 'DOMICILIATION'),
                ('ACH/201809', 'ASSURANCE'),
                ('ACH/201809', 'ASSURANCE'),
                ('ACH/201809', 'PARTNER 01'),
                ('ACH/201809', 'PARTNER 01'),
                ('ACH/201809', 'PARTNER 01'),
                ('ACH/201809', 'PARTNER 01'),
                ('ACH/201809', 'PARTNER 01'),
                ('ACH/201809', 'PARTNER 01'),
                ('ACH/201809', 'PARTNER 01'),
            ])

    def test_unbalanceable_moves(self):
        """ Test that the imbalanced moves raise as they cannot be balanced by day/month """

        self._attach_file_to_wizard(self.test_content_imbalanced_none, self.wizard)
        with self.assertRaises(UserError):
            self.wizard._import_files(['account.account', 'account.journal', 'res.partner', 'account.move'])

    def test_positive_montant_devise(self):
        """
        Test that it doesn't fail even when the MontantDevise is not signed, i.e. MontantDevise is positive even
        when the line is credited, or the opposite case: MontantDevise is negative while the line is
        debited.
        """
        test_content = """
            JournalCode\tJournalLib\tEcritureNum\tEcritureDate\tCompteNum\tCompteLib\tCompAuxNum\tCompAuxLib\tPieceRef\tPieceDate\tEcritureLib\tDebit\tCredit\tEcritureLet\tDateLet\tValidDate\tMontantdevise\tIdevise
            ACH\tACHATS\tTEST_MONTANT_DEVISE\t20180808\t62270000\tFRAIS D'ACTES ET CONTENTIEUX\t\t\t1\t20180808\tACOMPTE FORMALITES ENTREPRISE\t100,00\t0,00\t\t\t20190725\t100,00\tEUR
            ACH\tACHATS\tTEST_MONTANT_DEVISE\t20180808\t44566000\tTVA SUR AUTRES BIEN ET SERVICE\t\t\t1\t20180808\tACOMPTE FORMALITES ENTREPRISE\t0,00\t100,00\t\t\t20190725\t100,00\tEUR
            ACH\tACHATS\tTEST_MONTANT_DEVISE2\t20180808\t62270000\tFRAIS D'ACTES ET CONTENTIEUX\t\t\t1\t20180808\tACOMPTE FORMALITES ENTREPRISE\t0,00\t100,00\t\t\t20190725\t-100,00\tEUR
            ACH\tACHATS\tTEST_MONTANT_DEVISE2\t20180808\t44566000\tTVA SUR AUTRES BIEN ET SERVICE\t\t\t1\t20180808\tACOMPTE FORMALITES ENTREPRISE\t100,00\t0,00\t\t\t20190725\t-100,00\tEUR
        """
        self._attach_file_to_wizard(test_content, self.wizard)
        self.wizard._import_files()

    def test_fec_import_multicompany(self):
        self.wizard._import_files(['account.account', 'account.journal', 'res.partner'])

        fr_company2 = self.setup_company_data("Company FR 2", chart_template=self.company.chart_template)['company']
        wizard2 = self.env['account.fec.import.wizard'].with_company(fr_company2).create({'company_id': fr_company2.id})
        self._attach_file_to_wizard(self.test_content, wizard2)
        wizard2._import_files()


    def test_fec_import_reconciliation(self):
        test_content = """
            JournalCode\tJournalLib\tEcritureNum\tEcritureDate\tCompteNum\tCompteLib\tCompAuxNum\tCompAuxLib\tPieceRef\tPieceDate\tEcritureLib\tDebit\tCredit\tEcritureLet\tDateLet\tValidDate\tMontantdevise\tIdevise
            ACH\tACHATS\tACH000001\t20180910\t62270000\tLegal costs and litigation\t\t\t3\t20180910\tPARTNER 01\t100,00\t0,00\t\t\t20190725\t\t
            ACH\tACHATS\tACH000001\t20180910\t40100000\tSuppliers\tPARTNER01\tPARTNER 01\t3\t20180910\tPARTNER 01\t0,00\t100,00\tAA\t\t20190725\t\t
            BNK\tBANQUE\tBNK000001\t20180808\t40100000\tSuppliers\tPARTNER01\tPARTNER 01\t1\t20180808\tPayment\t100,00\t0,00\tAA\t\t20190725\t\t
            BNK\tBANQUE\tBNK000001\t20180808\t51200000\tBanque\t\t\t1\t20180808\tPayment\t0,00\t100,00\t\t\t20190725\t\t
            ACH\tACHATS\tACH000002\t20180910\t62270000\tLegal costs and litigation\t\t\t3\t20180910\tPARTNER 01\t100,00\t0,00\t\t\t20190725\t\t
            ACH\tACHATS\tACH000002\t20180910\t40100000\tSuppliers\tPARTNER01\tPARTNER 01\t3\t20180910\tPARTNER 01\t0,00\t100,00\tBB\t\t20190725\t\t
            BNK\tBANQUE\tBNK000002\t20180808\t40100000\tSuppliers\tPARTNER01\tPARTNER 01\t1\t20180808\tPayment\t100,00\t0,00\tBB\t\t20190725\t\t
            BNK\tBANQUE\tBNK000002\t20180808\t51200000\tBanque\t\t\t1\t20180808\tPayment\t0,00\t100,00\t\t\t20190725\t\t
        """
        self._attach_file_to_wizard(test_content, self.wizard)
        last = self.env['account.move'].search([], order='id desc', limit=1)
        self.wizard._import_files()
        new = self.env['account.move'].search([('id', '>', last.id)])
        self.assertEqual(len(new), 4)
        self.assertFalse(new.line_ids.full_reconcile_id, "Reconciliation is only temporary before posting")
        new.action_post()
        self.assertEqual(len(new.line_ids.full_reconcile_id), 2, "It is fully reconciled after posting")

    def test_key_is_empty(self):
        test_content = """
           JournalLib\tEcritureNum\tEcritureDate\tCompteNum\tCompteLib\tCompAuxNum\tCompAuxLib\tPieceRef\tPieceDate\tEcritureLib\tDebit\tCredit\tEcritureLet\tDateLet\tValidDate\tMontantdevise\tIdevise
            ACHATS\tACH000001\t20180910\t62270000\tLegal costs and litigation\t\t\t3\t20180910\tPARTNER 01\t100,00\t0,00\t\t\t20190725\t\t
            ACHATS\tACH000001\t20180910\t40100000\tSuppliers\tPARTNER01\tPARTNER 01\t3\t20180910\tPARTNER 01\t0,00\t100,00\tAA\t\t20190725\t\t
            BANQUE\tBNK000001\t20180808\t40100000\tSuppliers\tPARTNER01\tPARTNER 01\t1\t20180808\tPayment\t100,00\t0,00\tAA\t\t20190725\t\t
            BANQUE\tBNK000001\t20180808\t51200000\tBanque\t\t\t1\t20180808\tPayment\t0,00\t100,00\t\t\t20190725\t\t
            ACHATS\tACH000002\t20180910\t62270000\tLegal costs and litigation\t\t\t3\t20180910\tPARTNER 01\t100,00\t0,00\t\t\t20190725\t\t
            ACHATS\tACH000002\t20180910\t40100000\tSuppliers\tPARTNER01\tPARTNER 01\t3\t20180910\tPARTNER 01\t0,00\t100,00\tBB\t\t20190725\t\t
            BANQUE\tBNK000002\t20180808\t40100000\tSuppliers\tPARTNER01\tPARTNER 01\t1\t20180808\tPayment\t100,00\t0,00\tBB\t\t20190725\t\t
            BANQUE\tBNK000002\t20180808\t51200000\tBanque\t\t\t1\t20180808\tPayment\t0,00\t100,00\t\t\t20190725\t\t
        """

        self._attach_file_to_wizard(test_content, self.wizard)
        with self.assertRaisesRegex(UserError, "journal not found"):
            self.wizard._import_files(['account.account', 'account.journal', 'res.partner', 'account.move'])

    def test_created_account_translation(self):
        test_content = """
            JournalCode|JournalLib|EcritureNum|EcritureDate|CompteNum|CompteLib|CompAuxNum|CompAuxLib|PieceRef|PieceDate|EcritureLib|Debit|Credit|EcritureLet|DateLet|ValidDate|Montantdevise|Idevise
            J|anouveaux|REC|20220101|10100000|Capital|||CEX0122|20220101|S.A.N.|10000|0|||20230629||
            J|anouveaux|REC|20220101|10120000|"Cap.souscrit appelé| non versé"|||CEX0122|20220101|S.A.N.|0|10000|||20230629||
        """

        self.env['res.lang']._activate_lang('fr_FR')
        self.env['account.account'].search([('name', '=', 'Subscribed capital - uncalled')]).unlink()
        self._attach_file_to_wizard(test_content, self.wizard)
        self.wizard._import_files(['account.account', 'account.journal', 'res.partner', 'account.move'])
        account = self.env['account.account'].search([('name', '=', 'Subscribed capital - uncalled')]).with_context(lang="fr_FR")

        self.assertEqual(account.name, 'Capital souscrit - non appelé')
