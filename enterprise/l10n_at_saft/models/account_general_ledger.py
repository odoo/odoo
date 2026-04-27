# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo.tools.misc import street_split

from odoo import api, models, _

class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)
        if self.env.company.account_fiscal_country_id.code == 'AT':
            options.setdefault('buttons', []).append({
                'name': _('SAF-T'),
                'sequence': 50,
                'action': 'export_file',
                'action_param': 'l10n_at_export_saft_to_xml',
                'file_export_type': _('XML')
            })

    @api.model
    def _l10n_at_prepare_saft_report_values(self, report, options):
        template_vals = self._saft_prepare_report_values(report, options)

        # mapping from saft_account.type to its description
        saft_account_type_dict = {
            "1": "aktives Bestandskonto",
            "2": "passives Bestandskonto",
            "3": "Aufwandskonto",
            "4": "Erlöskonto",
        }

        # check that each account is mapped to exactly one SAF-T account
        accounts_with_mapping_problem = self.env['account.account']
        for account_vals in template_vals['account_vals_list']:

            account = account_vals['account']

            code_tags = account.tag_ids.filtered(lambda tag: tag.name.isnumeric())
            if not code_tags:
                accounts_with_mapping_problem |= account
                continue

            if len(code_tags) > 1:
                accounts_with_mapping_problem |= account

            code = code_tags[0].name
            # the search result is limited since the data may be loaded multiple times (each install / update)
            saft_account = self.env['l10n_at_saft.account'].search([
                ('code', '=', code)
            ], limit=1)
            if saft_account:
                account_vals.update({
                    'saft_type': saft_account_type_dict[saft_account.account_type],
                    'saft_code': saft_account.code,
                    'saft_description': saft_account.name,
                })
            else:
                accounts_with_mapping_problem |= account
        if accounts_with_mapping_problem:
            template_vals['errors']['accounts_not_found'] = {
                'message': _('Some accounts can not be mapped to an account from the chart of accounts given in the SAF-T specification (see the documentation for more information):'),
                'action_text': _('Check Accounts'),
                'action': accounts_with_mapping_problem._get_records_action(
                    name=_("Accounts which cannot be mapped into the SAF-T chart of accounts")),
            }

        taxtype_dict = defaultdict(lambda: {
            'description': None,
            'vals': [],
        })
        type_description_map = dict(self.env['account.tax'].fields_get()['type_tax_use']['selection'])
        unsupported_tax_ids = []
        for tax_vals in template_vals['tax_vals_list']:
            if tax_vals['amount_type'] != 'percent':
                unsupported_tax_ids.append(tax_vals['id'])

            tax_type = tax_vals['type']
            type_item = taxtype_dict[tax_type]
            type_item['description'] = type_description_map[tax_type]
            type_item['vals'].append(tax_vals)

        if unsupported_tax_ids:
            template_vals['errors']['amount_type_not_percentage'] = {
                'message': _('Taxes that are not percentages are not supported.'),
                'action_text': _('Check Taxes'),
                'action': (self.env['account.tax'].browse(unsupported_tax_ids)
                               ._get_records_action(name=_("Unsupported taxes"))),
                'level': 'danger',
            }

        accounting_basis = {
            'par_4_abs_1': "§ 4(1) EStG",
            'par_5': "§ 5 EStG",
        }.get(self.env.company.l10n_at_profit_assessment_method, "")

        template_vals.update({
            'xmlns': 'urn:OECD:StandardAuditFile-Taxation:AT_1.01',
            'file_version': '1.01',
            'accounting_basis': accounting_basis,
            'oenace_code': self.env.company.l10n_at_oenace_code or "",
            'kleinunternehmer_AT': '0',
            'taxtype_dict': taxtype_dict,
            'street_split': street_split,
        })

        missing_company_settings = []
        if not self.env.company.l10n_at_profit_assessment_method:
            missing_company_settings.append(_("profit assessment method"))
        if not self.env.company.l10n_at_oenace_code:
            missing_company_settings.append(_("ÖNACE-code"))

        if missing_company_settings:
            template_vals['errors']['missing_company_settings'] = {
                'message': _('Please define the %s in the accounting settings:', ', '.join(missing_company_settings)),
                'action_text': _('Go to Settings'),
                'action': self.env['res.config.settings']._get_records_action(name="Settings"),
            }

        company_contact = self.env['res.partner']
        if contacts := template_vals['partner_detail_map'][self.env.company.partner_id.id]['contacts']:
            company_contact |= contacts[0]
        if company_contact and not (company_contact.phone or company_contact.mobile):
            template_vals['errors']['missing_partner_phone_number'] = {
                'message': _('Please define a phone or mobile phone number for your company contact.'),
                'action_text': _('Check Company'),
                'action': company_contact._get_records_action(name=_("Missing Company Data")),
            }

        partner_without_complete_address_ids = []
        for (partner_id, partner_detail) in template_vals['partner_detail_map'].items():
            complete_addresses = [partner for partner in partner_detail['addresses']
                                  if partner.street and partner.city and partner.zip and partner.country_id]
            if not complete_addresses:
                partner_without_complete_address_ids.append(partner_id)
        if partner_without_complete_address_ids:
            template_vals['errors']['missing_partner_address'] = {
                'message': _('The addresses (street, city, postal code, country) of some partners are incomplete:'),
                'action_text': _('Check Partners'),
                'action': (self.env['res.partner'].browse(partner_without_complete_address_ids)
                                                  ._get_records_action(name=_("Invalid Partner"))),
            }

        return template_vals

    @api.model
    def l10n_at_export_saft_to_xml(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        template_values = self._l10n_at_prepare_saft_report_values(report, options)
        file_data = report._generate_file_data_with_error_check(
            options,
            self.env['ir.qweb']._render,
            {'values': template_values, 'template': 'l10n_at_saft.saft_template_inherit_l10n_at_saft', 'file_type': 'xml'},
            template_values['errors'],
        )
        return file_data
