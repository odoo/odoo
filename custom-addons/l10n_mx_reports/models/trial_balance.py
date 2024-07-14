# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from lxml import etree
from lxml.objectify import fromstring
from collections import defaultdict

from odoo import models, fields, _
from odoo.exceptions import UserError, RedirectWarning

CFDIBCE_XSLT_CADENA = 'l10n_mx_reports/data/xslt/1.3/BalanzaComprobacion_1_2.xslt'


class TrialBalanceCustomHandler(models.AbstractModel):
    _inherit = 'account.trial.balance.report.handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options)
        if self.env.company.account_fiscal_country_id.code == 'MX':
            options['buttons'] += [
                {'name': _("SAT (XML)"), 'action': 'export_file', 'action_param': 'action_l10n_mx_generate_sat_xml', 'file_export_type': _("SAT (XML)"), 'sequence': 15},
                {'name': _("COA SAT (XML)"), 'action': 'export_file', 'action_param': 'action_l10n_mx_generate_coa_sat_xml', 'file_export_type': _("COA SAT (XML)"), 'sequence': 16},
            ]

    def action_l10n_mx_generate_sat_xml(self, options):
        if self.env.company.account_fiscal_country_id.code != 'MX':
            raise UserError(_("Only Mexican company can generate SAT report."))

        sat_values = self._l10n_mx_get_sat_values(options)
        file_name = f"{sat_values['vat']}{sat_values['year']}{sat_values['month']}BN"
        cfdi = self.env['ir.qweb']._render('l10n_mx_reports.cfdibalance', sat_values)
        sat_report = self._l10n_mx_edi_add_digital_stamp(CFDIBCE_XSLT_CADENA, cfdi)

        self.env['ir.attachment'].l10n_mx_reports_validate_xml_from_attachment(sat_report, 'xsd_mx_cfdibalance_1_3.xsd')

        return {
            'file_name': f"{file_name}.xml",
            'file_content': etree.tostring(sat_report, pretty_print=True, xml_declaration=True, encoding='utf-8'),
            'file_type': 'xml',
        }

    def _l10n_mx_edi_add_digital_stamp(self, path_xslt, cfdi):
        """Add digital stamp certificate attributes in XML report"""
        tree = fromstring(cfdi)
        certificate = self.env.company.l10n_mx_edi_certificate_ids.sudo()._get_valid_certificate()
        if not certificate:
            return tree
        cadena = certificate._get_cadena_chain(tree, path_xslt)
        sello = certificate.sudo()._get_encrypted_cadena(cadena)
        tree.attrib['Sello'] = sello
        tree.attrib['noCertificado'] = certificate.serial_number
        tree.attrib['Certificado'] = certificate.sudo()._get_data()[0]
        return tree

    def _l10n_mx_get_sat_values(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        sat_options = self._l10n_mx_get_sat_options(options)
        report_lines = report._get_lines(sat_options)

        # The SAT code has to be of the form XXX.YY . Any additional suffixes are allowed, but if the line starts
        # with anything else it should not be included in the SAT report.
        sat_code = re.compile(r'((\d{3})\.\d{2})')

        account_lines = []
        parents = defaultdict(lambda: defaultdict(int))
        for line in [line for line in report_lines if line.get('level') == 4]:
            dummy, res_id = report._get_model_info_from_id(line['id'])
            account = self.env['account.account'].browse(res_id)
            is_credit_account = any([account.account_type.startswith(acc_type) for acc_type in ['liability', 'equity', 'income']])
            balance_sign = -1 if is_credit_account else 1
            cols = line.get('columns', [])
            # Initial Debit - Initial Credit = Initial Balance
            initial = balance_sign * (cols[0].get('no_format', 0.0) - cols[1].get('no_format', 0.0))
            # Debit and Credit of the selected period
            debit = cols[2].get('no_format', 0.0)
            credit = cols[3].get('no_format', 0.0)
            # End Debit - End Credit = End Balance
            end = balance_sign * (cols[4].get('no_format', 0.0) - cols[5].get('no_format', 0.0))
            pid_match = sat_code.match(line['name'])
            if not pid_match:
                raise UserError(_("Invalid SAT code: %s", line['name']))
            for pid in pid_match.groups():
                parents[pid]['initial'] += initial
                parents[pid]['debit'] += debit
                parents[pid]['credit'] += credit
                parents[pid]['end'] += end
        for pid in sorted(parents.keys()):
            account_lines.append({
                'number': pid,
                'initial': '%.2f' % parents[pid]['initial'],
                'debit': '%.2f' % parents[pid]['debit'],
                'credit': '%.2f' % parents[pid]['credit'],
                'end': '%.2f' % parents[pid]['end'],
            })

        report_date = fields.Date.to_date(sat_options['date']['date_from'])
        return {
            'vat': self.env.company.vat or '',
            'month': str(report_date.month).zfill(2),
            'year': report_date.year,
            'type': 'N',
            'accounts': account_lines,
        }

    def action_l10n_mx_generate_coa_sat_xml(self, options):
        if self.env.company.account_fiscal_country_id.code != 'MX':
            raise UserError(_("Only Mexican company can generate SAT report."))

        coa_values = self._l10n_mx_get_coa_values(options)
        file_name = f"{coa_values['vat']}{coa_values['year']}{coa_values['month']}CT"
        coa_report = etree.fromstring(self.env['ir.qweb']._render('l10n_mx_reports.cfdicoa', coa_values))

        self.env['ir.attachment'].l10n_mx_reports_validate_xml_from_attachment(coa_report, 'xsd_mx_cfdicoa_1_3.xsd')

        return {
            'file_name': f"{file_name}.xml",
            'file_content': etree.tostring(coa_report, pretty_print=True, xml_declaration=True, encoding='utf-8'),
            'file_type': 'xml',
        }

    def _l10n_mx_get_coa_values(self, options):
        # Checking if debit/credit tags are installed
        debit_balance_account_tag = self.env.ref('l10n_mx.tag_debit_balance_account', raise_if_not_found=False)
        credit_balance_account_tag = self.env.ref('l10n_mx.tag_credit_balance_account', raise_if_not_found=False)
        if not debit_balance_account_tag or not credit_balance_account_tag:
            raise UserError(_("Missing Debit or Credit balance account tag in database."))

        coa_options = self._l10n_mx_get_sat_options(options)
        accounts = self.env['account.account'].search([
            *self.env['account.account']._check_company_domain(self.env.company),
            ('account_type', '!=', 'equity_unaffected'),
            ('group_id', '!=', False),
        ])
        accounts_groups_by_parent = defaultdict(lambda: defaultdict(lambda: self.env['account.account']))
        accounts_template_data = []
        for account in accounts:
            accounts_groups_by_parent[account.group_id.parent_id][account.group_id] |= account
        no_tag_accounts = self.env['account.account']
        multi_tag_accounts = self.env['account.account']
        parent_nature = ''
        for parent, accounts_by_group in accounts_groups_by_parent.items():
            parent_nature = set()
            group_lines = []
            for group, accounts in accounts_by_group.items():
                group_nature = set()
                for account in accounts:
                    nature = ''
                    if debit_balance_account_tag in account.tag_ids:
                        nature += 'D'
                    if credit_balance_account_tag in account.tag_ids:
                        nature += 'A'
                    if not nature:
                        no_tag_accounts |= account
                    elif len(nature) > 1:
                        multi_tag_accounts |= account
                    else:
                        group_nature.add(nature)
                if len(group_nature) > 1:
                    multi_tag_accounts |= accounts

                group_nature = len(group_nature) and group_nature.pop()
                group_lines.append({
                    'code': group.code_prefix_start,
                    'number': group.code_prefix_start,
                    'name': group.name,
                    'level': 2,
                    'nature': group_nature,
                })
                if group_nature:
                    parent_nature.add(group_nature)

            if len(parent_nature) > 1:
                for accounts in accounts_by_group.values():
                    multi_tag_accounts |= accounts
            parent_nature = len(parent_nature) and parent_nature.pop()
            parent_line = [{
                'code': parent.code_prefix_start,
                'number': parent.code_prefix_start,
                'name': parent.name,
                'level': 1,
                'nature': parent_nature,
            }]
            accounts_template_data += parent_line + group_lines
        if no_tag_accounts:
            raise RedirectWarning(
                _("Some accounts present in your trial balance don't have a Debit or a Credit balance account tag."),
                {
                    'name': _("Accounts without tag"),
                    'type': 'ir.actions.act_window',
                    'views': [(False, 'list'), (False, 'form')],
                    'res_model': 'account.account',
                    'target': 'current',
                    'domain': [('id', 'in', no_tag_accounts.ids)],
                },
                _('Show list')
            )
        if multi_tag_accounts:
            raise RedirectWarning(
                _("Some account prefixes used in your trial balance use both Debit and Credit balance account tags. This is not allowed."),
                {
                    'name': _("Accounts with too much tags"),
                    'type': 'ir.actions.act_window',
                    'views': [(False, 'list'), (False, 'form')],
                    'res_model': 'account.account',
                    'target': 'current',
                    'domain': [('id', 'in', multi_tag_accounts.ids)],
                },
                _('Show list')
            )
        report_date = fields.Date.to_date(coa_options['date']['date_from'])
        return {
            'vat': self.env.company.vat or '',
            'month': str(report_date.month).zfill(2),
            'year': report_date.year,
            'accounts': accounts_template_data,
        }

    def _l10n_mx_get_sat_options(self, options):
        sat_options = options.copy()
        del sat_options['comparison']
        return self.env['account.report'].browse(options['report_id']).get_options(
            previous_options={
                **sat_options,
                'hierarchy': True,  # We need the hierarchy activated to get group lines
            }
        )
