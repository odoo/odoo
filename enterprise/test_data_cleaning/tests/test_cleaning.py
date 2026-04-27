# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import test_common

class TestCleaning(test_common.TestCommon):
    def test_cleaning_action_trim_all(self):
        jean_claude = self._create_record('data_cleaning.test.model', name='jean claude')
        self._create_record('data_cleaning.test.model', name='bernard')

        self._create_rule('trim', action_trim='all', field_name='name')
        self.TestDCModel.action_clean_records()

        records_found = self.Record.search([('cleaning_model_id', '=', self.TestDCModel.id)])
        self.assertEqual(len(records_found), 1, 'Should find 1 record to clean')

        self.assertEqual(records_found.res_id, jean_claude.id, 'Should clean jean claude')
        self.assertEqual(records_found.suggested_value, 'jeanclaude', 'Should remove all spaces in jean claude')

        records_found.action_validate()
        self.assertEqual(jean_claude.name, 'jeanclaude', 'should update the name of jeanclaude')

    def test_cleaning_action_trim_superfluous(self):
        jean_claude = self._create_record('data_cleaning.test.model', name='     jean   claude     ')
        self._create_record('data_cleaning.test.model', name='bernard')

        self._create_rule('trim', action_trim='superfluous', field_name='name')
        self.TestDCModel.action_clean_records()

        records_found = self.Record.search([('cleaning_model_id', '=', self.TestDCModel.id)])
        self.assertEqual(len(records_found), 1, 'Should find 1 record to clean')

        self.assertEqual(records_found.res_id, jean_claude.id, 'Should clean jean claude')
        self.assertEqual(records_found.suggested_value, 'jean claude', 'Should remove spaces in jean claude')

        records_found.action_validate()
        self.assertEqual(jean_claude.name, 'jean claude', 'should update the name to jean claude')

    def test_cleaning_action_case_first(self):
        self._create_record('data_cleaning.test.model', name='Jean Claude')
        bernard = self._create_record('data_cleaning.test.model', name='BERNARD')

        self._create_rule('case', action_case='first', field_name='name')
        self.TestDCModel.action_clean_records()

        records_found = self.Record.search([('cleaning_model_id', '=', self.TestDCModel.id)])
        self.assertEqual(len(records_found), 1, 'Should find 1 record to clean')

        self.assertEqual(records_found.res_id, bernard.id, 'Should be BERNARD!')
        self.assertEqual(records_found.suggested_value, 'Bernard', 'Should change to all lowercase with B in caps')

        records_found.action_validate()
        self.assertEqual(bernard.name, 'Bernard', 'should update the name to Bernard')

    def test_cleaning_action_case_first_translated(self):
        bernard = self._create_record('data_cleaning.test.model', name='Bernard', translated_field="THIS IS BERNARD")
        bernard.with_context(lang='fr_FR').translated_field = "C'EST BERNARD"

        self._create_rule('case', action_case='first', field_name='translated_field')
        self.TestDCModel.action_clean_records()

        records_found = self.Record.search([('cleaning_model_id', '=', self.TestDCModel.id)])
        self.assertEqual(len(records_found), 1, 'Should find 1 record to clean')

        self.assertEqual(records_found.res_id, bernard.id, 'Should be `THIS IS BERNARD`!')
        self.assertEqual(records_found.suggested_value, 'This Is Bernard', 'Should change to all lowercase with first letters in caps')

        records_found.action_validate()
        self.assertEqual(bernard.translated_field, 'This Is Bernard', 'should update the translated_field to `This Is Bernard`')
        self.assertEqual(bernard.with_context(lang='fr_FR').translated_field, "C'EST BERNARD", 'shoudn\'t update the translated_field of other languages')

    def test_cleaning_action_case_upper(self):
        jean_claude = self._create_record('data_cleaning.test.model', name='Jean Claude')
        self._create_record('data_cleaning.test.model', name='BERNARD')

        self._create_rule('case', action_case='upper', field_name='name')
        self.TestDCModel.action_clean_records()

        records_found = self.Record.search([('cleaning_model_id', '=', self.TestDCModel.id)])
        self.assertEqual(len(records_found), 1, 'Should find 1 record to clean')

        self.assertEqual(records_found.res_id, jean_claude.id, 'Should be Jean Claude!')
        self.assertEqual(records_found.suggested_value, 'JEAN CLAUDE', 'Should change to all uppercase')

        records_found.action_validate()
        self.assertEqual(jean_claude.name, 'JEAN CLAUDE', 'should update the name to JEAN CLAUDE')

    def test_cleaning_action_case_lower(self):
        jean_claude = self._create_record('data_cleaning.test.model', name='Jean Claude')
        bernard = self._create_record('data_cleaning.test.model', name='BERNARD')

        self._create_rule('case', action_case='lower', field_name='name')
        self.TestDCModel.action_clean_records()

        records_found = self.Record.search([('cleaning_model_id', '=', self.TestDCModel.id)])
        self.assertEqual(len(records_found), 2, 'Should find 2 records to clean')

        self.assertEqual(records_found.mapped('res_id'), [jean_claude.id, bernard.id], 'Should be Jean Claude and BERNARD!')

        records_found.action_validate()
        self.assertEqual(jean_claude.name, 'jean claude', 'should update the name to jean claude')
        self.assertEqual(bernard.name, 'bernard', 'should update the name to bernard')

    def test_cleaning_action_phone(self):
        country_be = self.env['res.country'].search([('code', '=', 'BE')])
        jc = self._create_record('data_cleaning.test.model', name='jc', phone='081 12 34 00', country_id=country_be.id)
        self._create_record('data_cleaning.test.model', name='jc2', phone='+32 470 12 34 00', country_id=country_be.id)

        self._create_rule('phone', field_name='phone')
        self.TestDCModel.action_clean_records()

        records_found = self.Record.search([('cleaning_model_id', '=', self.TestDCModel.id)])
        self.assertEqual(len(records_found), 1, 'Should find 1 record to clean')

        self.assertEqual(records_found.suggested_value, '+32 81 12 34 00', 'It should add Belgium\'s country code')

        records_found.action_validate()
        self.assertEqual(jc.phone, '+32 81 12 34 00', 'should save the formated number')

    def test_cleaning_action_html(self):
        note_html = "h<b>e</b><i>l</i><marquee>lo</marquee> <script>alert('pownez')</script>"
        note_txt = "h*e* l lo  alert('pownez')"
        rec = self._create_record('data_cleaning.test.model', note=note_html)
        self._create_record('data_cleaning.test.model', note='1 is < than 2 and 2 is > than 1')

        self._create_rule('html', field_name='note')
        self.TestDCModel.action_clean_records()

        records_found = self.Record.search([('cleaning_model_id', '=', self.TestDCModel.id)])
        self.assertEqual(len(records_found), 1, 'Should find 1 record to clean')

        self.assertEqual(records_found.suggested_value, note_txt, 'It should strip HTML')

        records_found.action_validate()
        self.assertEqual(rec.note, note_txt, 'should save without the html')

    def test_cleaning_multiple_actions(self):
        jc = self._create_record('data_cleaning.test.model', name='jean         claude       ')

        self._create_rule('trim', action_trim='all', field_name='name', sequence=10)
        self._create_rule('case', action_case='first', field_name='name', sequence=0)
        self.TestDCModel.action_clean_records()

        records_found = self.Record.search([('cleaning_model_id', '=', self.TestDCModel.id)])
        self.assertEqual(len(records_found), 1, 'Should find 1 record to clean')

        self.assertEqual(records_found.suggested_value, 'JeanClaude', 'should be JeanClaude')

        records_found.action_validate()
        self.assertEqual(jc.name, 'JeanClaude', 'should save the correct value')

    def test_cleaning_action_phone_country(self):
        country_be = self.env['res.country'].search([('code', '=', 'BE')])
        company = self.env['res.company'].create({
            'name': 'be company',
            'country_id': country_be.id
        })

        jc = self._create_record('data_cleaning.test.model', name='jc', phone='081 12 34 00', country_id=False, company_id=company.id)
        self.assertEqual(jc.country_id, self.env['res.country'], 'no country should be set')

        self._create_rule('phone', field_name='phone')
        self.TestDCModel.action_clean_records()

        records_found = self.Record.search([('cleaning_model_id', '=', self.TestDCModel.id)])
        self.assertEqual(len(records_found), 1, 'Should find 1 record to clean')

        self.assertEqual(records_found.country_id, country_be, 'It should take the country of the company')
        self.assertEqual(records_found.suggested_value, '+32 81 12 34 00', 'It should add Belgium\'s country code')

    def test_automatic_cleaning(self):
        self.TestDCModel.update({'cleaning_mode': 'automatic'})

        jc = self._create_record('data_cleaning.test.model', name='jean claude')
        bernard = self._create_record('data_cleaning.test.model', name='B E r N A    RD')
        gisele = self._create_record('data_cleaning.test.model', name='gisEle')

        self._create_rule('trim', action_trim='all', field_name='name', sequence=10)
        self._create_rule('case', action_case='first', field_name='name', sequence=0)
        self.TestDCModel.action_clean_records()

        records_found = self.Record.search([('cleaning_model_id', '=', self.TestDCModel.id)])
        self.assertEqual(len(records_found), 0, 'no records should be found')

        self.assertEqual(jc.name, 'JeanClaude', 'Name should be changed')
        self.assertEqual(bernard.name, 'BERNARd', 'Name should be changed')
        self.assertEqual(gisele.name, 'Gisele', 'Name should be changed')
