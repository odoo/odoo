# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io

from lxml import etree
import re

from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def create_document_from_attachment(self, attachment_ids=None):
        # OVERRIDE
        journal = self or self.browse(self.env.context.get('default_journal_id'))
        if journal.type == 'general':
            attachments = self.env['ir.attachment'].browse(attachment_ids or [])
            if not attachments:
                raise UserError(_("No attachment was provided"))
            if all(journal._l10n_be_check_soda_format(attachment) for attachment in attachments):
                return journal._l10n_be_parse_soda_file(attachments)
        return super().create_document_from_attachment(attachment_ids)

    def _l10n_be_check_soda_format(self, attachment):
        try:
            return (
                (attachment.mimetype in ('application/xml', 'text/xml')
                # XML files sent by email have text/plain as mimetype
                or (attachment.mimetype == 'text/plain' and attachment.name.lower().endswith('.xml')))
                and etree.parse(io.BytesIO(attachment.raw)).getroot().tag == 'SocialDocument'
            )
        except etree.XMLSyntaxError:
            return False

    def _l10n_be_parse_soda_file(self, attachments, skip_wizard=False):
        self.ensure_one()
        # We keep a dict mapping the SODA reference to a dict with a list of `entries` and an `attachment_id`
        # {
        #     'soda_reference_1': {
        #         'entries': [
        #             {
        #                 'code': '1200',
        #                 'name': 'Line Description',
        #                 'debit': '150.0',
        #                 'credit': '0.0',
        #             },
        #             ...
        #         ],
        #         'attachment_id': 'attachment_id_1',
        #     },
        #     ...
        # }
        soda_files = {}
        soda_code_to_name_mapping = {}
        for attachment in attachments:
            parsed_attachment = etree.parse(io.BytesIO(attachment.raw))
            # The document VAT number must match the journal's company's VAT number
            journal_company_vat = self.company_id.company_registry or self.company_id.vat and re.search(r'\d+', self.company_id.vat).group()
            parsed_ent_num = parsed_attachment.find('.//EntNum')
            ent_num = parsed_ent_num.text and re.search(r'\d+', parsed_ent_num.text).group()
            if ent_num != journal_company_vat:
                if len(attachments) == 1:
                    message = _('The Soda Entry could not be created: \n'
                                'The imported document doesn\'t seem to correspond to this company\'s VAT number nor company id')
                else:
                    message = _('The SODA Entry could not be created: \n'
                                'The company VAT number found in at least one document doesn\'t seem to correspond to this company\'s VAT number nor company id')
                raise UserError(message)
            # account.move.ref is SocialNumber+SequenceNumber+AccountPeriodYYYY/AccountPeriodmm : check that this move has not already been imported
            account_period = parsed_attachment.find('.//AccountPeriod').text
            ref = "%s-%s-%s/%s" % (parsed_attachment.find('.//Source').text, parsed_attachment.find('.//SeqNumber').text, account_period[:4], account_period[4:])
            existing_move = self.env['account.move'].search([('ref', '=', ref)])
            if existing_move:
                if self._context.get('raise_no_imported_file', True):
                    raise UserError(
                        _('The entry %s has already been uploaded (%s).', ref, existing_move.name))
                else:
                    return
            soda_files[ref] = {
                'entries': [],
                'attachment_id': attachment.id,
                'date': parsed_attachment.findtext('.//GenDate') or fields.Date.today().strftime("%Y-%m-%d"),
            }
            # Retrieve aml's infos
            for _idx, elem in enumerate(parsed_attachment.findall('.//Accounting')):
                code = elem.find('./Account').text
                name = elem.find('./Label').text
                soda_files[ref]['entries'].append({
                    'code': code,
                    'name': name,
                    'debit': float(elem.find('./Amount/Debit').text),
                    'credit': float(elem.find('./Amount/Credit').text),
                })
                soda_code_to_name_mapping[code] = name

        wizard = self.env['soda.import.wizard'].create({
            'soda_files': soda_files,
            'soda_code_to_name_mapping': soda_code_to_name_mapping,
            'company_id': self.company_id.id,
            'journal_id': self.id,
        })
        if skip_wizard:
            return wizard._action_save_and_import()
        return {
            'name': _('SODA Import'),
            'type': 'ir.actions.act_window',
            'views': [(False, 'form')],
            'view_mode': 'form',
            'view_id': self.env.ref('l10n_be_soda.soda_import_wizard_view_form').id,
            'res_model': 'soda.import.wizard',
            'res_id': wizard.id,
            'target': 'new',
        }
