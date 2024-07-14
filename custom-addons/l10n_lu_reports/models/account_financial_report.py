# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from odoo import fields, models, _
from odoo.tools.float_utils import float_compare, float_repr
from odoo.exceptions import UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta


class LuxembourgishFinancialReportCustomHandler(models.AbstractModel):
    _name = 'l10n_lu.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Luxembourgish Financial Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options.setdefault('buttons', []).append(
            {'name': _('XML'), 'sequence': 30, 'action': 'open_report_export_wizard_accounts_report'}
        )

    def get_report_filename(self, options):
        # we can't determine milliseconds using fields.Datetime, hence used python's `datetime`
        company = self.env.company
        agent = company.account_representative_id
        now_datetime = datetime.now()
        file_ref_data = {
            'ecdf_prefix': agent and agent.l10n_lu_agent_ecdf_prefix or company.ecdf_prefix,
            'datetime': now_datetime.strftime('%Y%m%dT%H%M%S%f')[:-4]
        }
        filename = '{ecdf_prefix}X{datetime}'.format(**file_ref_data)
        # `FileReference` element of exported XML must have same `filename` as above. So, we pass it from
        # here and get it from options in `_get_lu_electronic_report_values` and pass it further to template.
        if options:
            options['filename'] = filename
        return filename

    def get_electronic_report_values(self, options):
        company = self.env.company
        report = self.env['account.report'].browse(options['report_id'])
        vat = report.get_vat_for_export(options, raise_warning=False)
        if vat and vat.startswith("LU"):  # Remove LU prefix in the XML
            vat = vat[2:]
        return {
            'filename': options.get('filename'),
            'lang': 'EN',
            'interface' : 'MODL5',
            'vat_number' : vat or "NE",
            'matr_number' : company.matr_number or "NE",
            'rcs_number' : company.company_registry or "NE",
        }

    def _validate_ecdf_prefix(self):
        ecdf_prefix = self.env.company.ecdf_prefix
        if not ecdf_prefix:
            raise UserError(_('Please set valid eCDF Prefix for your company.'))
        re_valid_prefix = re.compile(r'[0-9|A-Z]{6}$')
        if not re_valid_prefix.match(ecdf_prefix):
            msg = _('eCDF Prefix `{0}` associated with `{1}` company is invalid.\nThe expected format is ABCD12 (Six digits of numbers or capital letters)')
            raise UserError(msg.format(ecdf_prefix, self.env.company.display_name))
        return True

    def _validate_xml_content(self, content):
        self.env['ir.attachment'].l10n_lu_reports_validate_xml_from_attachment(content, 'ecdf')
        return True

    def get_financial_reports(self):
        return {
            self.env.ref("l10n_lu_reports.account_financial_report_l10n_lu_bs").id : 'CA_BILAN',
            self.env.ref("l10n_lu_reports.account_financial_report_l10n_lu_bs_abr").id : 'CA_BILANABR',
            self.env.ref("l10n_lu_reports.account_financial_report_l10n_lu_pl").id : 'CA_COMPP',
            self.env.ref("l10n_lu_reports.account_financial_report_l10n_lu_pl_abr").id : 'CA_COMPPABR'
        }

    def get_financial_electronic_report_values(self, options):

        def _format_amount(amount):
            return float_repr(amount, 2).replace('.', ',') if amount else '0,00'

        values = {}

        def _report_useful_fields(amount, field, parent_field, required):
            """Only reports fields containing values or that are required."""
            # All required fields are always reported; all others reported only if different from 0.00.
            if float_compare(amount, 0.0, 2) != 0 or required:
                values.update({field: {'value': _format_amount(amount), 'field_type': 'number'}})
                # The parent needs to be added even if at 0, if some child lines are filled in
                if parent_field and not values.get(parent_field):
                    values.update({parent_field: {'value': '0,00', 'field_type': 'number'}})

        report = self.env['account.report'].browse(options['report_id'])
        lu_template_values = self.get_electronic_report_values(options)

        # Add comparison filter to get data from last year
        options = report.get_options({**options, 'comparison': {
            'filter': 'same_last_year',
            'number_period': 1,
        }})

        lines = report._get_lines(options)

        report_line = self.env['account.report.line']
        date_from = fields.Date.from_string(options['date'].get('date_from'))
        date_to = fields.Date.from_string(options['date'].get('date_to'))
        values.update({
            '01': {'value': date_from.strftime("%d/%m/%Y"), 'field_type': 'char'},
            '02': {'value': date_to.strftime("%d/%m/%Y"), 'field_type': 'char'},
            '03': {'value': self.env.company.currency_id.name, 'field_type': 'char'}
        })

        # we only need `account.report.line` records' IDs, so we need to check the model
        # as some of these could be `account.account` records
        for line in lines:
            model, res_id = self.env['account.report']._get_model_info_from_id(line['id'])
            if model != 'account.report.line':
                continue

            # financial report's `code` would contain alpha-numeric string like `LU_BS_XXX/LU_BSABR_XXX`
            # where characters at last three positions will be digits, hence we split with `_`
            # and build dictionary having `code` as dictionary key
            split_line_code = (report_line.browse(res_id).code or '').split('_') or []
            columns = line['columns']
            # since we have enabled comparison by default, `columns` element will atleast have two dictionary items.
            # First dict will be holding current year's balance and second one will be holding previous year's balance.
            if len(split_line_code) > 2:
                parent_code = None
                parent_id = report_line.browse(res_id).parent_id
                if parent_id and parent_id.code:
                    parent_split_code = parent_id.code.split('_')
                    if len(parent_split_code) > 2:
                        parent_code = parent_split_code[2]

                required = line['level'] == 0 or split_line_code[2] in ['201', '202', '405', '406']
                # current year balance
                _report_useful_fields(columns[0]['no_format'], split_line_code[2], parent_code, required)
                # previous year balance
                _report_useful_fields(columns[1]['no_format'], str(int(split_line_code[2]) + 1), parent_code and str(int(parent_code) + 1), required)

        lu_template_values.update({
            'forms': [{
                'declaration_type': self.get_financial_reports()[report.id],
                'year': date_from.year,
                'period': "1",
                'field_values': values
            }]
        })
        return lu_template_values

    def export_to_xml(self, options):
        self._validate_ecdf_prefix()

        lu_template_values = self.get_financial_electronic_report_values(options)

        rendered_content = self.env['ir.qweb']._render('l10n_lu_reports.l10n_lu_electronic_report_template_2_0', lu_template_values)
        content = "\n".join(re.split(r'\n\s*\n', rendered_content))
        self._validate_xml_content(content)

        return {
            'file_name': self.env['account.report'].browse(options['report_id']).get_report_filename(options) + '.xml',
            'file_content':  "<?xml version='1.0' encoding='UTF-8'?>" + content,
            'file_type': 'xml',
        }

    def get_xml_2_0_report_values(self, options, references=False):
        """Returns the formatted report values for this financial report.
           (Balance sheet: https://ecdf-developer.b2g.etat.lu/ecdf/forms/popup/CA_BILAN_COMP/2020/en/2/preview),
            Profit&Loss: https://ecdf-developer.b2g.etat.lu/ecdf/forms/popup/CA_COMPP_COMP/2020/en/2/preview)
           Adds the possibility to add references to the report and the form model number to
           get_electronic_report_values.

           :param options: the report options
           :param references: whether the annotations on the financial report should be added to the report as references
           :returns: the formatted report values
        """
        def _get_references(report):
            """
            This returns the annotations on all financial reports, linked to the corresponding report reference field.
            These will be used as references in the report.
            """
            references = {}
            names = {}
            notes = self.env['account.report.manager'].search([
                ('company_id', '=', self.env.company.id),
                ('report_id', '=', report.id)
            ]).footnotes_ids
            for note in notes:
                # for footnotes on accounts on financial reports, the line field will be:
                # 'financial_report_group_xxx_yyy', with xxx the line id and yyy the account id
                split = note.line.split('_')
                if len(split) > 1 and split[-2].isnumeric() and split[-1].isnumeric():
                    line = self.env['account.report.line'].search([('id', '=', split[-2])], limit=1)
                    code = re.search(r'\d+', str(line.code))
                    if code:
                        # References in the eCDF report have codes equal to the report code of the referred account + 1000
                        code = str(int(code.group()) + 1000)
                        references[code] = {'value': note.text, 'field_type': 'char'}
                        names[code] = self.env['account.account'].search([("id", "=", split[-1])]).mapped('code')[0]
            return references, names

        report = self.env['account.report'].browse(options['report_id'])
        if not self.env.context.get('skip_options_recompute'):
            options = report.get_options(options)
        lu_template_values = self.get_financial_electronic_report_values(options)
        for form in lu_template_values['forms']:
            if references:
                references, names = _get_references(report)
                # Only add those references on accounts with reported values (for the current or previous year);
                # the reference has an eCDF code equal to the report code of the referred account for the current year + 1000,
                # to equal to the report code of the ref. account for the previous year + 999
                references = {r: references[r] for r in references
                              if str(int(r) - 1000) in form['field_values'] or str(int(r) - 999) in form['field_values']}
                names = {r: names[r] for r in references
                         if str(int(r) - 1000) in form['field_values'] or str(int(r) - 999) in form['field_values']}
                # Check the length of the references <= 10 (XML report limit)
                if any([len(r['value']) > 10 for r in references.values()]):
                    raise UserError(
                        _("Some references are not in the requested format (max. 10 characters):") + "\n    " +
                        "\n    ".join([names[i[0]] + ": " + i[1]['value'] for i in references.items() if len(i[1]['value']) > 10]) +
                        "\n" + _("Cannot export them.")
                    )
                for ref in references:
                    form['field_values'].update({ref: references[ref]})
            model = 2 if form['year'] == 2020 else 1
            form['model'] = model
        return lu_template_values['forms']

    def open_report_export_wizard_accounts_report(self, options):
        """ Creates a new export wizard for this report."""
        new_context = self.env.context.copy()
        new_context['report_generation_options'] = options
        return {
            'type': 'ir.actions.act_window',
            'name': _('Export'),
            'view_mode': 'form',
            'res_model': 'l10n_lu.generate.accounts.report',
            'target': 'new',
            'views': [[self.env.ref('l10n_lu_reports.view_l10n_lu_generate_accounts_report').id, 'form']],
            'context': new_context,
        }
