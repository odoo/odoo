# -*- coding: utf-8 -*-

from freezegun import freeze_time

from odoo.addons.l10n_es_reports.tests.common import TestEsAccountReportsCommon
from odoo import fields
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestBOEGeneration(TestEsAccountReportsCommon):
    """ Basic tests checking the generation of BOE files is still possible.
    """

    def _check_boe_111_to_303(self, modelo_number):
        self.init_invoice('out_invoice', partner=self.spanish_partner, amounts=[10000], invoice_date=fields.Date.today(), taxes=self.spanish_test_tax, post=True)
        report = self.env.ref('l10n_es.mod_%s' % modelo_number)
        report.filter_multi_company = 'disabled'
        options = self._generate_options(report, fields.Date.from_string('2020-12-01'), fields.Date.from_string('2020-12-31'))
        self._check_boe_export(report, options, modelo_number)

    @freeze_time('2020-12-22')
    def test_boe_mod_111(self):
        self._check_boe_111_to_303('111')

    @freeze_time('2020-12-22')
    def test_boe_mod_115(self):
        self._check_boe_111_to_303('115')

    @freeze_time('2020-12-22')
    def test_boe_mod_303(self):
        self._check_boe_111_to_303('303')

    @freeze_time('2020-12-22')
    def test_boe_mod_347(self):
        invoice = self.init_invoice('out_invoice', partner=self.spanish_partner, amounts=[10000], invoice_date=fields.Date.today())
        invoice.l10n_es_reports_mod347_invoice_type = 'regular'
        invoice._post()
        spanish_partner_2 = self.env['res.partner'].create({
            # ES Partner with vat not starting with 'ES', should still be included in 347
            'name': 'Partner 2',
            'street': "Avenida de los Informes Financieros, 43",
            'zip': 4242,
            'city': "Madrid",
            'country_id': self.env.ref('base.es').id,
            'state_id': self.env.ref('base.state_es_m').id,
            'vat': '74280274A',
        })
        invoice_2 = self.init_invoice('out_invoice', partner=spanish_partner_2, amounts=[5000], invoice_date=fields.Date.today())
        invoice_2.action_post()
        invoice_3 = self.init_invoice('out_invoice', partner=spanish_partner_2, amounts=[4000], invoice_date=fields.Date.today())
        invoice_3.l10n_es_reports_mod347_invoice_type = 'insurance'
        invoice_3._post()
        report = self.env.ref('l10n_es_reports.mod_347')
        report.filter_multi_company = 'disabled'
        options = self._generate_options(report, fields.Date.from_string('2020-01-01'), fields.Date.from_string('2020-12-31'))
        self._check_boe_export(report, options, 347)

        # Check file content
        report._get_lines(options)
        handler = self.env[report.custom_handler_model_name]
        vals = handler.export_boe(options)
        expected = [
            # For information about data position, see page 7 & 16 of
            # https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro/DR_300_399/archivos/347.pdf
            # 1,347,year,company vat
            "13472020A12345674COMPANY_1_DATA                          T         BECAUSE I AM ACCOUNTMAN!                3470000000002  0000000000000000000002 000000001900000000000000 000000000000000                                                                                                                                                                                                                                                                                                                           ",
            # 2,347,year,company vat,partner vat
            "23472020A1234567474280274A         PARTNER 2                               D28   B 000000000400000X 000000000000000 0000000000000000000 000000000000000 000000000000000 000000000000000 000000000000000 000000000000000 000000000000000 000000000400000 000000000000000                     000000000000000000000                                                                                                                                                                                                   ",
            "23472020A12345674A12345674         BERNARDO GANADOR                        D28   B 000000001000000  000000000000000 0000000000000000000 000000000000000 000000000000000 000000000000000 000000000000000 000000000000000 000000000000000 000000001000000 000000000000000                     000000000000000000000                                                                                                                                                                                                   ",
            "23472020A1234567474280274A         PARTNER 2                               D28   B 000000000500000  000000000000000 0000000000000000000 000000000000000 000000000000000 000000000000000 000000000000000 000000000000000 000000000000000 000000000500000 000000000000000                     000000000000000000000                                                                                                                                                                                                   ",
        ]
        for generated_line, expected_line in zip(vals['file_content'].decode('utf-8').splitlines(), expected):
            self.assertEqual(generated_line, expected_line)

        handler._retrieve_boe_manual_wizard(options, 347).write({
            'complementary_declaration': True,
            'substitutive_declaration': True,
        })
        vals = handler.export_boe(options)
        header_line = vals['file_content'].decode('utf-8').splitlines()[0]
        self.assertEqual('C', header_line[120], "Complementary declaration should use 'C'")
        self.assertEqual('S', header_line[121], "Substitutive declaration should use 'S'")

    @freeze_time('2020-12-22')
    def test_boe_mod_349(self):
        self.partner_a.write({
            'country_id': self.env.ref('base.be').id,
            'vat': "BE0477472701",
        })
        invoice = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[10000], invoice_date=fields.Date.today())
        invoice.l10n_es_reports_mod349_invoice_type = 'E'
        invoice._post()
        report = self.env.ref('l10n_es_reports.mod_349')
        report.filter_multi_company = 'disabled'
        options = self._generate_options(report, fields.Date.from_string('2020-12-01'), fields.Date.from_string('2020-12-31'))
        self._check_boe_export(report, options, 349)

    @freeze_time('2020-12-22')
    def test_boe_mod_390(self):
        report = self.env.ref('l10n_es.mod_390')
        options = self._generate_options(report, '2020-01-01', '2020-12-31')
        self._check_boe_export(report, options, 390, additional_context={
            'default_physical_person_name': "Bernard Gagnant",
            'default_principal_activity': "Selling",
            'default_principal_iae_epigrafe': "EAAA",
            'default_principal_code_activity': "AAA",
            'default_judicial_person_name': "Bebert",
            'default_judicial_person_nif': "123",
            'default_judicial_person_procuration_date': '2020-01-01',
            'default_judicial_person_notary': "Maître Gagnant",
        })

    @freeze_time('2020-12-22')
    def test_boe_mod_347_with_cash_payment(self):
        cash_journal = self.env['account.journal'].create({
            'name': 'Cash Journal Test',
            'type': 'cash',
            'company_id': self.company_data['company'].id,
            'code': 'CASHBOE',
        })
        invoice = self.init_invoice('out_invoice', partner=self.spanish_partner, amounts=[1000], invoice_date=fields.Date.today())
        invoice.l10n_es_reports_mod347_invoice_type = 'regular'
        invoice._post()
        self.env['account.payment.register'].with_context(active_ids=invoice.ids, active_model='account.move').create({
            'amount': 1000,
            'payment_date': invoice.date,
            'journal_id': cash_journal.id,
        })._create_payments()

        report = self.env.ref('l10n_es_reports.mod_347')
        options = self._generate_options(report, '2020-01-01', '2020-12-31')
        wizard_model = self.env[report.custom_handler_model_name]
        wizard_action = wizard_model.open_boe_wizard(options, 347)
        wizard = self.env[wizard_action['res_model']].with_context(wizard_action['context']).create({})
        options['l10n_es_reports_boe_wizard_id'] = wizard.id

        boe_result = self.env[report.custom_handler_model_name].export_boe(options)
        self.assertTrue(self.spanish_partner.name.upper() not in boe_result['file_content'].decode())

    @freeze_time('2025-05-15')
    def test_boe_includes_null_lines_mod_349(self):
        """
        Test that the mod 349 boe report contains the rectification lines even when the total rectification sum to 0
        """
        partner = self.env['res.partner'].create({
            'name': 'Test',
            'company_id': self.company_data['company'].id,
            'company_type': 'company',
            'country_id': self.env['res.country'].search([('code', '=', 'BE')]).id,
            'vat': 'BE0477472701',
        })
        invoice = self.init_invoice('out_invoice', partner=partner, amounts=[1000], invoice_date='2025-03-15')
        invoice.action_post()

        credit_note_wizard = self.env['account.move.reversal'].with_context({
            'active_ids': invoice.id,
            'active_id': invoice.id,
            'active_model': 'account.move',
        }).create({
            'reason': 'modify',  # 'reason' can still be used to indicate purpose
            'journal_id': invoice.journal_id.id,
        })
        credit_note_wizard.modify_moves()

        report = self.env.ref('l10n_es_reports.mod_349')
        options = self._generate_options(report, fields.Date.from_string('2025-05-01'), fields.Date.from_string('2025-05-31'))
        wizard_action = self.env['l10n_es.mod349.tax.report.handler'].open_boe_wizard(options, '349')
        wizard = self.env[wizard_action['res_model']].with_context(wizard_action['context']).create({})
        options['l10n_es_reports_boe_wizard_id'] = wizard.id

        boe_file = self.env['l10n_es.mod349.tax.report.handler'].export_boe(options)

        # This string represents a rectification record included in the BOE export.
        # It contains:
        # - the year (2025),
        # - the period,
        # - the rectified tax base (0.00),
        # - and the previously declared tax base (1000.00).
        # Under REGISTRO DE RECTIFICACIONES https://www.boe.es/buscar/doc.php?id=BOE-A-2010-5098
        self.assertIn('20250300000000000000000000100000', boe_file['file_content'].decode('utf-8'))

    @freeze_time('2025-05-15')
    def test_only_include_credit_note_in_rectification_mod_349(self):
        """
        Test that in model 349 only the credit notes are included in the computation of the rectification line
        """
        partner = self.env['res.partner'].create({
            'name': 'Test',
            'company_id': self.company_data['company'].id,
            'company_type': 'company',
            'country_id': self.env['res.country'].search([('code', '=', 'BE')]).id,
            'vat': 'BE0477472701',
        })

        invoice = self.init_invoice('out_invoice', partner=partner, amounts=[1000], invoice_date='2025-03-15')
        invoice.action_post()

        reversal_wizard = self.env['account.move.reversal'].with_context({
            'active_ids': invoice.id,
            'active_id': invoice.id,
            'active_model': 'account.move',
        }).create({
            'reason': 'refund',
            'journal_id': invoice.journal_id.id,
        })
        reversal = reversal_wizard.reverse_moves()
        refund = self.env['account.move'].browse(reversal.get('res_id'))
        refund.line_ids.write({'price_unit': 500.0})
        refund.action_post()

        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'amount': 250.0,
        })._create_payments()

        report = self.env.ref('l10n_es_reports.mod_349')
        options = self._generate_options(report, fields.Date.from_string('2025-05-01'), fields.Date.from_string('2025-05-31'))
        wizard_action = self.env['l10n_es.mod349.tax.report.handler'].open_boe_wizard(options, '349')
        wizard = self.env[wizard_action['res_model']].with_context(wizard_action['context']).create({})
        options['l10n_es_reports_boe_wizard_id'] = wizard.id

        boe_file = self.env['l10n_es.mod349.tax.report.handler'].export_boe(options)

        # Those strings represent a rectification record included in the BOE export.
        # It contains:
        # - the year (2025),
        # - the period,
        # - the rectified tax base (0.00),
        # - and the previously declared tax base (1000.00).
        # Under REGISTRO DE RECTIFICACIONES https://www.boe.es/buscar/doc.php?id=BOE-A-2010-5098

        # Here the new value should be 500 and not 250 because the payment should not count in the rectification line
        self.assertIn('20250300000000500000000000100000', boe_file['file_content'].decode('utf-8'))
        self.assertNotIn('20250300000000250000000000100000', boe_file['file_content'].decode('utf-8'))

    @freeze_time('2025-05-15')
    def test_boe_excludes_current_period_rectification_lines(self):
        """
        Test that moves from the current period are not included as rectification lines in the boe report
        """
        partner = self.env['res.partner'].create({
            'name': 'Test',
            'company_id': self.company_data['company'].id,
            'company_type': 'company',
            'country_id': self.env['res.country'].search([('code', '=', 'BE')]).id,
            'vat': 'BE0477472701',
        })
        previous_period_invoice = self.init_invoice('out_invoice', partner=partner, amounts=[1000], invoice_date='2025-03-15')
        previous_period_invoice.action_post()

        credit_note_wizard_previous = self.env['account.move.reversal'].with_context({
            'active_ids': previous_period_invoice.id,
            'active_id': previous_period_invoice.id,
            'active_model': 'account.move',
        }).create({
            'reason': 'modify',
            'journal_id': previous_period_invoice.journal_id.id,
        })
        credit_note_wizard_previous.reverse_moves()

        current_period_invoice = self.init_invoice('out_invoice', partner=partner, amounts=[1000], invoice_date='2025-05-15')
        current_period_invoice.action_post()

        credit_note_wizard_current = self.env['account.move.reversal'].with_context({
            'active_ids': current_period_invoice.id,
            'active_id': current_period_invoice.id,
            'active_model': 'account.move',
        }).create({
            'reason': 'modify',
            'journal_id': current_period_invoice.journal_id.id,
        })
        credit_note_wizard_current.reverse_moves()

        report = self.env.ref('l10n_es_reports.mod_349')
        options = self._generate_options(report, fields.Date.from_string('2025-05-01'), fields.Date.from_string('2025-05-31'))
        wizard_action = self.env['l10n_es.mod349.tax.report.handler'].open_boe_wizard(options, '349')
        wizard = self.env[wizard_action['res_model']].with_context(wizard_action['context']).create({})
        options['l10n_es_reports_boe_wizard_id'] = wizard.id

        boe_file = self.env['l10n_es.mod349.tax.report.handler'].export_boe(options)
        # This string represents a rectification record included in the BOE export.
        # It contains:
        # - the year (2025),
        # - the period (here 5 which is the current period),
        # - the rectified tax base (0.00),
        # - and the previously declared tax base (1000.00).
        # Under REGISTRO DE RECTIFICACIONES https://www.boe.es/buscar/doc.php?id=BOE-A-2010-5098
        self.assertNotIn('20250500000000000000000000100000', boe_file['file_content'].decode('utf-8'))
