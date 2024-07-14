# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import re
from odoo import models, fields, tools, _
from odoo.exceptions import RedirectWarning, ValidationError


class L10nLuGenerateXML(models.TransientModel):
    """
    This wizard is used to generate xml reports for Luxembourg
    according to the xml 2.0 standard.
    """
    _name = 'l10n_lu.generate.xml'
    _description = 'Generate Xml 2.0'

    report_data = fields.Binary('Report file', readonly=True, attachment=False)
    filename = fields.Char(string='Filename', size=256, readonly=True)

    def get_xml(self, lu_annual_report=False):
        """
        Generates the XML report.
        lu_annual_report contains the report id of the manual annual report.
        """
        company = self.env.company
        agent = company.account_representative_id

        # Check for agent's required fields
        if agent:
            ecdf_not_ok = not agent.l10n_lu_agent_ecdf_prefix or not re.match('[0-9A-Z]{6}', agent.l10n_lu_agent_ecdf_prefix)
            matr_not_ok = not agent.l10n_lu_agent_matr_number or not re.match('[0-9]{11,13}', agent.l10n_lu_agent_matr_number)
            if ecdf_not_ok or matr_not_ok:
                raise RedirectWarning(
                    message=_("Some fields required for the export are missing or invalid. Please verify them."),
                    action={
                        'name': _("Company: %s", agent.name),
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'res_model': 'res.partner',
                        'views': [[False, 'form']],
                        'target': 'new',
                        'res_id': agent.id,
                        'context': {'create': False},
                    },
                    button_text=_('Verify'),
                    additional_context={'required_fields': [ecdf_not_ok and 'l10n_lu_agent_ecdf_prefix',
                                                            matr_not_ok and 'l10n_lu_agent_matr_number']}
                )
        report_gen_options = self.env.context.get('report_generation_options', {})
        report = self.env['account.report'].browse(report_gen_options.get('report_id'))
        options = report.get_options({**report_gen_options, 'export_mode': 'file'})
        filename = self.env['l10n_lu.report.handler'].get_report_filename(options)
        agent_vat = agent.vat if agent else self._get_export_vat()
        company_vat = self._get_export_vat()
        agent_vat = agent_vat[2:] if agent_vat and agent_vat.startswith("LU") else agent_vat
        company_vat = company_vat[2:] if company_vat and company_vat.startswith("LU") else company_vat
        language = self.env.context.get('lang', '').split('_')[0].upper()
        language = language in ('EN', 'FR', 'DE') and language or 'EN'
        if report_gen_options:
            report_gen_options['language'] = language
        lu_template_values = {
            'filename': filename,
            'lang': language,
            'interface': 'MODL5',
            'agent_vat': agent_vat or "NE",
            'agent_matr_number': agent.l10n_lu_agent_matr_number or company.matr_number or "NE",
            'agent_rcs_number': agent.l10n_lu_agent_rcs_number or company.company_registry or "NE",
            'declarations': []
        }
        # The Matr. Number is required
        if not company.matr_number:
            raise RedirectWarning(
                message=_(
                    "The company's Matr. Number hasn't been defined. Please configure it in the company's information."
                ),
                action={
                    'name': _("Company: %s", company.name),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'res.company',
                    'views': [[False, 'form']],
                    'target': 'new',
                    'res_id': company.id,
                    'context': {'create': False},
                },
                button_text=_('Configure'),
                additional_context={'required_fields': ['matr_number']}
            )
        if not company.ecdf_prefix:
            raise ValidationError(_("The ECDF Prefix hasn't been defined. Please add the ECDF prefix in the company's information."))

        declaration_template_values = {
            'vat_number': company_vat or "NE",
            'matr_number': company.matr_number or "NE",
            'rcs_number': company.company_registry or "NE",
        }
        declarations_data = self._lu_get_declarations(declaration_template_values)
        self._save_xml_report(declarations_data, lu_template_values, filename)
        url = "web/content/?model=" + self._name + "&id=" + str(
            self.id) + "&filename_field=filename&field=report_data&download=true&filename=" + self.filename

        return {
                    'name': 'XML Report',
                    'type': 'ir.actions.act_url',
                    'url': url,
                    'target': 'new',
                }

    def _lu_get_declarations(self, declaration_template_values):
        """
        To override in specific report generation
        """
        raise NotImplementedError("This method must be implemented in a subclass.")

    def _get_export_vat(self):
        # To be overridden for reports that need to allow foreign VAT fiscal positions
        return self.env.company.vat

    def _save_xml_report(self, declarations_data, lu_template_values, filename, lu_annual_report=False):
        lu_template_values['declarations'] = declarations_data['declarations']

        # Add function to format floats
        lu_template_values['format_float'] = lambda f: tools.float_utils.float_repr(f, 2).replace('.', ',')
        rendered_content = self.env['ir.qweb']._render('l10n_lu_reports.l10n_lu_electronic_report_template_2_0', lu_template_values, minimal_qcontext=True)

        content = "\n".join(re.split(r'\n\s*\n', rendered_content))
        self.env['ir.attachment'].l10n_lu_reports_validate_xml_from_attachment(content, 'ecdf')
        self.env['l10n_lu.report.handler']._validate_ecdf_prefix()
        vals = {
            'report_data': base64.b64encode(bytes("<?xml version='1.0' encoding='UTF-8'?>" + content, 'utf-8')),
            'filename': filename + '.xml'
        }
        if lu_annual_report:
            lu_annual_report.write(vals)
        else:
            self.write(vals)
