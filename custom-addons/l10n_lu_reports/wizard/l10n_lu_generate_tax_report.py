# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare
from dateutil.relativedelta import relativedelta
from ..models.l10n_lu_tax_report_data import (YEARLY_SIMPLIFIED_NEW_TOTALS, YEARLY_SIMPLIFIED_FIELDS,
                                              YEARLY_MONTHLY_FIELDS_TO_DELETE, VAT_MANDATORY_FIELDS)

class L10nLuGenerateTaxReport(models.TransientModel):
    """This wizard generates an xml tax report for Luxemburg according to the xml 2.0 standard."""
    _inherit = 'l10n_lu.generate.xml'
    _name = 'l10n_lu.generate.tax.report'
    _description = 'Generate Tax Report'

    simplified_declaration = fields.Boolean(default=True)
    # field used to show the correct button in the view
    period = fields.Selection(
        [('A', 'Annual'), ('M', 'Monthly'), ('T', 'Quarterly')],
    )

    @api.model
    def default_get(self, default_fields):
        rec = super().default_get(default_fields)
        options = self.env.ref('l10n_lu.tax_report').get_options()
        date_from = fields.Date.from_string(options['date'].get('date_from'))
        date_to = fields.Date.from_string(options['date'].get('date_to'))

        mapping = {
            date_from + relativedelta(months=12, days=-1): 'A',
            date_from + relativedelta(months=3, days=-1): 'T',
            date_from + relativedelta(months=1, days=-1): 'M',
        }

        rec['period'] = mapping.get(date_to)
        if not rec['period']:
            raise ValidationError(
                _("The fiscal period you have selected is invalid, please verify. Valid periods are : Month, Quarter and Year."))

        return rec

    def _get_export_vat(self):
        report = self.env.ref('l10n_lu.tax_report')
        options = report.get_options()
        return report.get_vat_for_export(options, raise_warning=False)

    def _lu_get_declarations(self, declaration_template_values):
        """
        Gets the formatted values for LU's tax report.
        Exact format depends on the period (monthly, quarterly, annual).
        """
        report_gen_options = self.env.context.get('report_generation_options', {})
        report = self.env['account.report'].browse(report_gen_options.get('sections_source_id'))
        # generate the initial form with the main report
        options = report.get_options({**report_gen_options, 'no_report_reroute': True})
        form = self.env[report.custom_handler_model_name].get_tax_electronic_report_values(options)['forms'][0]
        for section in report.section_report_ids:
            section_options = section.get_options({
                **options,
                'selected_section_id': section.id,
                'export_mode': 'file',
                'unfold_all': True,
            })
            form['field_values'].update(self.env[report.custom_handler_model_name].get_tax_electronic_report_values(section_options)['forms'][0]['field_values'])

        on_payment = self.env['account.tax'].search([
            *self.env['account.tax']._check_company_domain(report.get_report_company_ids(options)),
            ('tax_exigibility', '=', 'on_payment')
        ], limit=1)

        form['field_values']['204'] = {'value': on_payment and '0' or '1', 'field_type': 'boolean'}
        form['field_values']['205'] = {'value': on_payment and '1' or '0', 'field_type': 'boolean'}
        for code, field_type in (
                ('403', 'number'), ('418', 'number'), ('453', 'number'), ('042', 'float'), ('416', 'float'), ('417', 'float'), ('451', 'float'), ('452', 'float')
            ):
            form['field_values'][code] = {'value': 0, 'field_type': field_type}

        self.period = form['declaration_type'][-1]
        form['field_values'] = self._remove_zero_fields(form['field_values'], report.id)
        if self.period == 'A':
            date_from = fields.Date.from_string(options['date'].get('date_from'))
            date_to = fields.Date.from_string(options['date'].get('date_to'))
            self._adapt_to_annual_report(form, date_from, date_to)
            if report == self.env.ref('l10n_lu_reports.l10n_lu_annual_tax_report'):
                self.simplified_declaration = False
                self._adapt_to_full_annual_declaration(form, options)
            else:
                self._adapt_to_simplified_annual_declaration(form)

        form['model'] = 1
        declaration = {'declaration_singles': {'forms': [form]}, 'declaration_groups': []}
        declaration.update(declaration_template_values)
        return {'declarations': [declaration]}

    def _add_yearly_fields(self, form, options):
        # add mandatory fields even if they are empty
        for code in VAT_MANDATORY_FIELDS - {'450', '801', '802'}:
            if code not in form:
                form[code] = {'value': 0.0, 'field_type': 'float'}

        char_fields = {
            '206': ['007'],
            '229': ['100'],
            '264': ['265', '266', '267', '268'],
            '273': ['274', '275', '276', '277'],
            '278': ['279', '280', '281', '282'],
            '318': ['319', '320'],
            '321': ['322', '323'],
            '357': ['358', '359'],
            '387': ['388'],
        }
        for field in char_fields:
            child_exists = any(form.get(related_field) for related_field in char_fields[field])
            if not form.get(field) and child_exists:
                raise ValidationError(_("The field %s must be filled because one of the dependent fields is filled in.", field))
            elif form.get(field) and not child_exists:
                form.pop(field, None)

        if form.get('389') and not form.get('010'):
            raise ValidationError(_("The field 010 in 'Other Assimilated Supplies' is mandatory if you fill in the field 389 in 'Appendix B'. Field 010 must be equal to field 389"))
        if form.get('369') or form.get('368'):
            if not form.get('369') or not form.get('368'):
                raise ValidationError(_("Both fields 369 and 368 must be either filled in or left empty (Appendix B)."))
            elif form.get('368') < form.get('369'):
                raise ValidationError(_("The field 369 must be smaller than field 368 (Appendix B)."))
        if form.get('388', False) ^ form.get('387', False):
            raise ValidationError(_("The field 387 must be filled in if field 388 is filled in and vice versa (Appendix B)."))
        if form.get('387', False) ^ form.get('388', False):
            raise ValidationError(_("The field 388 must be filled in if field 387 is filled in  and vice versa (Appendix B)."))

        if form.get('163') and form.get('165') and not form.get('164'):
            form['164'] = {'value': form.get('163') - form.get('165'), 'field_type': 'float'}
        elif form.get('163') and form.get('164') and not form.get('165'):
            form['165'] = {'value': form.get('163') - form.get('164'), 'field_type': 'float'}
        elif (form.get('163') and not form.get('164') and not form.get('165')) or (form.get('163', 0) != form.get('164', 0) + form.get('165', 0)):
            raise ValidationError(_("Fields 164 and 165 are mandatory when 163 is filled in and must add up to field 163 (Appendix E)."))

        if not form['361']['value']:
            form['361'] = form['414']
        if not form['362']['value']:
            form['362'] = form['415']
        if float_compare(form['361']['value'], 0.0, 2) != 0 and '192' not in form:
            form['192'] = form['361']
        if float_compare(form['362']['value'], 0.0, 2) != 0 and '193' not in form:
            form['193'] = form['362']
        if ('192' in form) ^ ('193' in form):
            form['192'] = form.get('192', {'value': 0.0, 'field_type': 'float'})
            form['193'] = form.get('193', {'value': 0.0, 'field_type': 'float'})

        # Add appendix to operational expenditures
        expenditures_table = []
        date_to = options['date']['date_to']
        year = fields.Date.from_string(date_to).year
        domain = [
            ('company_id', 'in', [comp['id'] for comp in options['companies']]),
            ('year', '=', year)
        ]
        appendix_lines = self.env['l10n_lu_reports.report.appendix.expenditures'].search_read(
            domain, fields=['report_section_411', 'report_section_412', 'report_section_413']
        )
        for appendix in appendix_lines:
            expenditures_table.append({
                '411': {'value': appendix['report_section_411'], 'field_type': 'char'},
                '412': {'value': appendix['report_section_412'], 'field_type': 'float'},
                '413': {'value': appendix['report_section_413'], 'field_type': 'float'},
            })

        return form, expenditures_table

    def _adapt_to_full_annual_declaration(self, form, options):
        """
        Adapts the report to the annual format, comprising additional fields and apppendices.
        (https://ecdf-developer.b2g.etat.lu/ecdf/forms/popup/TVA_DECA_TYPE/2020/en/1/preview)
        """
        # Check the correct allocation of monthly fields
        field_values = form['field_values']
        allocation_dict = {}
        for monthly_field in ('472', '455', '456', '457', '458', '459', '460', '461'):
            allocation_dict[monthly_field] = field_values.get(monthly_field, {'value': 0.0})

        rest = [k for k, v in allocation_dict.items() if float_compare(v['value'], 0.0, 2) != 0]
        if rest:
            raise ValidationError(_("The following monthly fields haven't been completely allocated yet: ") + str(rest))

        field_values, expenditures = self._add_yearly_fields(field_values, options)
        if expenditures:
            form['tables'] = [expenditures]

        # Character fields
        if not field_values.get('007') and field_values.get('206'):
            # Only fill in field 206 (additional Total Sales/Receipts line), which specifies what field
            # 007 refers to, if 007 has something to report
            field_values.pop('206', None)

        # Field 010 (use of goods considered business assets for purposes other than those of the business) is specified
        # in the annex part B: we put everything in "Other assets" (field 388) and specify that in the detail line (field 387)
        if field_values.get('010'):
            field_values['387'] = {'value': 'Report from 010', 'field_type': 'char'}

        # Remove monthly fields
        for f in YEARLY_MONTHLY_FIELDS_TO_DELETE:
            field_values.pop(f, None)

    def _adapt_to_simplified_annual_declaration(self, form):
        """
        Adapts the tax report (built for the monthly tax report) to the format required
        for the simplified annual tax declaration.
        (https://ecdf-developer.b2g.etat.lu/ecdf/forms/popup/TVA_DECAS_TYPE/2020/en/1/preview)
        """
        form['declaration_type'] = 'TVA_DECAS'
        for total, addends in YEARLY_SIMPLIFIED_NEW_TOTALS.items():
            form['field_values'][total] = {
                'value': sum([form['field_values'].get(a) and float(str(form['field_values'][a]['value']).replace(',', '.')) or 0.00 for a in addends]),
                'field_type': 'float'}
        # "Supply of goods by a taxable person applying the common flat-rate scheme for farmers" fields are not supported;
        form['field_values']['801'] = {'value': 0.00, 'field_type': 'float'}
        form['field_values']['802'] = {'value': 0.00, 'field_type': 'float'}
        # Only keep valid declaration fields
        form['field_values'] = {k: v for k, v in form['field_values'].items() if k in YEARLY_SIMPLIFIED_FIELDS}

    def _get_account_code(self, ln):
        model, active_id = self.env['account.report']._get_model_info_from_id(ln['id'])
        if model == 'account.account':
            account_code = self.env['account.account'].browse(active_id).code
            return account_code
        return False

    def _get_account_name(self, ln):
        _, active_id = self.env['account.report']._get_model_info_from_id(ln['id'])
        return self.env['account.account'].browse(active_id).name

    @api.model
    def _adapt_to_annual_report(self, form, date_from, date_to):
        """Adds date fields specific to annual tax reports in LU."""
        form['field_values'].update({
            '233': {'value': str(date_from.day), 'field_type': 'number'},
            '234': {'value': str(date_from.month), 'field_type': 'number'},
            '235': {'value': str(date_to.day), 'field_type': 'number'},
            '236': {'value': str(date_to.month), 'field_type': 'number'}
        })

    def _remove_zero_fields(self, field_values, report_id):
        """Removes declaration fields at 0, unless they are mandatory fields or parents of filled-in fields."""
        parents = self.env['account.report.line'].search([('report_id', '=', report_id)]).mapped(
                lambda r: (r.code, r.parent_id.code)
        )
        parents_dict = {p[0]: p[1] for p in parents}
        new_field_values = {}
        for f in field_values:
            if f in VAT_MANDATORY_FIELDS or field_values[f]['field_type'] not in ('float', 'number', 'char')\
                    or (field_values[f]['field_type'] == 'number' and field_values[f]['value'] != '0,00')\
                    or (field_values[f]['field_type'] == 'float' and float_compare(field_values[f]['value'], 0.0, 2) != 0)\
                    or (field_values[f]['field_type'] == 'char' and field_values[f]['value'] != ''):
                new_field_values[f] = field_values[f]
                # If a field is filled in, the parent should be filled in too, even if at 0.00;
                parent = parents_dict.get('LUTAX_' + f)
                if parent and not new_field_values.get(parent[6:]):
                    new_field_values[parent[6:]] = {'value': '0,00', 'field_type': 'number'}
        return new_field_values
