from odoo import models, _
from lxml import etree
from datetime import date

from odoo.exceptions import UserError


class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        if self.env.company.account_fiscal_country_id.code == 'BE':
            options['buttons'].append({
                'name': _('Annual Accounts'),
                'sequence': 40,
                'action': 'export_file',
                'action_param': 'l10n_be_get_annual_accounts',
                'file_export_type': _('XML'),
            })


    def l10n_be_get_annual_accounts(self, options):
        """ Export the general ledger as XML following the TussentijdseStaat XSD format. """
        report = self.env['account.report'].with_context(no_format=True).browse(options['report_id'])
        print_options = report.get_options(previous_options=options)

        # Get the lines of the report, then filter to only use the account lines (the other aren't needed.)
        lines = report._get_lines(print_options)
        account_lines = []
        account_ids = []
        for line in lines:
            model, account_id = report._parse_line_id(line['id'])[-1][1:]
            if model != 'account.account':
                continue
            account_lines.append(line)
            account_ids.append(account_id)
        accounts = self.env['account.account'].browse(account_ids).grouped('id')

        # As we export for the current period, only the first column group is relevant
        column_group = list(options.get('column_groups', {}).keys())[0]
        columns = options.get('columns', [])
        column_name_to_index = {col['expression_label']: idx for idx, col in enumerate(columns) if col['column_group_key'] == column_group}

        def _get_account_name_in_lang(account, lang_code):
            ''' Get the account name in the specified language.
            If the language is not available, it will return the default name.
            To avoid user errors when the language is not available.
            '''
            try:
                return account.with_context(lang=lang_code).name or ""
            except UserError:
                return account.name or ""

        root = etree.Element("TussentijdseStaat")
        etree.SubElement(root, "Versie").text = "1.0"
        accounts_el = etree.SubElement(root, "Rekeningen")
        for line in account_lines:
            __, account_id = report._get_model_info_from_id(line['id'])
            account = accounts.get(account_id)
            debit = str(line['columns'][column_name_to_index['debit']]['no_format'])
            credit = str(line['columns'][column_name_to_index['credit']]['no_format'])

            account_el = etree.SubElement(accounts_el, "Rekening")
            etree.SubElement(account_el, "DiverseOperatie").text = ""
            etree.SubElement(account_el, "RekeningNummer").text = account.code or ""
            etree.SubElement(account_el, "BedragCredit").text = credit
            etree.SubElement(account_el, "BedragDebet").text = debit
            etree.SubElement(account_el, "OmschrijvingNederlands").text = _get_account_name_in_lang(account, 'nl_BE')
            etree.SubElement(account_el, "OmschrijvingFrans").text = _get_account_name_in_lang(account, 'fr_BE')
            etree.SubElement(account_el, "OmschrijvingEngels").text = _get_account_name_in_lang(account, 'en_US')
            etree.SubElement(account_el, "OmschrijvingDuits").text = _get_account_name_in_lang(account, 'de_DE')

        etree.SubElement(root, "Datum").text = date.today().isoformat()
        etree.SubElement(root, "Omschrijving").text = _("Annual Balance Report")
        etree.SubElement(root, "Herkomst").text = "Odoo"

        return {
            'file_name': 'annual_accounts.xml',
            'file_content': etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=True),
            'file_type': 'xml',
        }
