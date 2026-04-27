import logging

from markupsafe import Markup

import base64

from odoo import api, fields, models, Command
from odoo.tools.float_utils import float_repr
from odoo.tools.translate import _


_logger = logging.getLogger(__name__)


class AECGenerator(models.TransientModel):
    _name = 'l10n_cl.aec.generator'
    _description = 'Chilean AEC Wizard Generator'

    partner_id = fields.Many2one(
        'res.partner', domain=[('l10n_cl_is_factoring', '=', True),
                               ('commercial_partner_id.l10n_cl_is_factoring', '=', True)],
        string='Factoring Company',
        required=True
    )
    invoice_date_due = fields.Date('Date Due', default=fields.Date.context_today)

    def _create_aec_account_entry(self, move, factoring_partner, invoice_date_due=None):
        account_entry = self.env['account.move'].create({
            'journal_id': move.company_id.l10n_cl_factoring_journal_id.id,
            'ref': _('Yield of invoice: %s', move.name),
            'date': fields.Date.context_today(self.with_context(tz='America/Santiago')),
            'move_type': 'entry',
            'l10n_cl_dte_status': 'not_sent'
        })
        lines_data = []
        for line in move.line_ids.filtered(lambda x: x.account_id.account_type == 'asset_receivable'):
            lines_data.append({
                'name': _('Yield of invoice %(invoice_name)s for partner %(partner_name)s',
                    invoice_name=move.name, partner_name=move.partner_id.name),
                'credit': line.debit,
                'debit': line.credit,
                'partner_id': line.partner_id.id,
                'account_id': line.account_id.id,
            })
        total_credit = sum(line['credit'] - line['debit'] for line in lines_data)
        counterpart_line = {
            'name': _('Yield of invoice %(invoice_name)s for partner %(partner_name)s',
                invoice_name=move.name, partner_name=move.partner_id.name),
            'account_id': move.company_id.l10n_cl_factoring_counterpart_account_id.id,
            'partner_id': factoring_partner.id,
            'date_maturity': invoice_date_due,
            'debit': total_credit,
        }
        lines_data.append(counterpart_line)
        account_entry.line_ids = [Command.create(data) for data in lines_data]
        return account_entry

    @api.model
    def _l10n_cl_create_aec(self, move, factoring_partner, invoice_date_due=None):
        # Create the account entry for the yield (this was the 4th step but we moved it as the main step)
        account_entry = self._create_aec_account_entry(move, factoring_partner, invoice_date_due)
        digital_signature = move.company_id.sudo()._get_digital_signature(user_id=self.env.user.id)
        # Signature number 1: Render the internal DTE file and sign it
        dte_file = move.sudo().l10n_cl_dte_file.raw.decode('ISO-8859-1')
        dte_file = dte_file.replace('<?xml version="1.0" encoding="ISO-8859-1" ?>\n', '')
        partner = self.env.user.partner_id
        base_values = {
            'move': move,
            'float_repr': float_repr,
            'signatory': {
                'vat': digital_signature.subject_serial_number,
                'name': partner.name,
                'email': partner.email,
            },
            'assignee': {
                'vat': factoring_partner.vat,
                'name': factoring_partner.name,
                'address': f"{factoring_partner.street} {factoring_partner.street2 or ''} {factoring_partner.city or ''}",
                'email': factoring_partner.email,
            },
            'company_id': move.company_id,
            'get_cl_current_strftime': move._get_cl_current_strftime,
            '__keep_empty_lines': True,
        }
        signed_aec = move._l10n_cl_render_and_sign_xml(
            'l10n_cl_edi_factoring.aec_template_yield_document', {**base_values, 'dte_file': Markup(dte_file)},
            'DTE_Cedido', 'dteced', digital_signature)

        # Signature number 2: Create the yield document template of the DTE above and sign it
        doc_id_contract = 'Odoo_Cesion_%s' % move.name.replace(' ', '_')
        # multiple factoring is not available at SII
        signed_doc = move._l10n_cl_render_and_sign_xml(
            'l10n_cl_edi_factoring.aec_template_yield_contract', {**base_values, 'sequence': 1},
            doc_id_contract, 'cesion', digital_signature)

        # Store the partial document as an attachment for the yield as an attachment of the invoice
        signed_yield = signed_aec + signed_doc
        account_entry.message_post(body=_('Created DTE Yielded intermediate file'))
        # remove intermediate attachment_ids=[yield_attachment.id]) because we don't create the file as attachment

        # Signature number 3: Render the AEC file and sign it
        signed_aec = self.env['ir.qweb']._render(
            'l10n_cl_edi_factoring.aec_template_yields',
            {**base_values, 'aec_document': signed_yield},
        )
        final_aec = move._l10n_cl_render_and_sign_xml(
            'l10n_cl_edi_factoring.aec_template',
            {'signed_aec': signed_aec, '__keep_empty_lines': True},
            'AEC', 'aec', digital_signature, without_xml_declaration=False)

        # Create the AEC attachment, with the AEC envelope. Now in the account entry
        timestamp = move._get_cl_current_strftime(date_format='%Y%m%d_%H%M%S')
        record_ref = move.name.replace(' ', '_')
        self.env['ir.attachment'].create(
            {
                "res_model": "account.move",
                "res_id": account_entry.id,
                "res_field": "l10n_cl_aec_attachment_file",
                "name": f'AEC_{record_ref}_{move.company_id.vat}_{timestamp}.xml',
                "datas": base64.b64encode(final_aec.encode('ISO-8859-1', 'replace')),
                "type": "binary",
            }
        )
        account_entry.message_post(
            body=_('AEC File has been created'), attachment_ids=account_entry.l10n_cl_aec_attachment_id.ids)

        # Post the entry, and link it to the invoice
        account_entry._post(soft=False)
        message_body_entry = (
            Markup('<p>{msg}<a href="#" data-oe-model="account.move" data-oe-id="{move_id}">{display_name}</a></p>')
            .format(
                msg=_("This is the yield account entry for the following invoice:"),
                move_id=move.id,
                display_name=move.display_name
            )
        )
        account_entry.message_post(body=message_body_entry, subtype_xmlid="mail.mt_note")
        # Reconcile the lines of this new account entry with each of the lines of the invoice
        receivable_accounts_in_moves = move.line_ids.filtered(
            lambda x: x.account_id.account_type == 'asset_receivable')
        for receivable_accounts_line, line in zip(
                receivable_accounts_in_moves, account_entry.line_ids.filtered(
                    lambda y: y.account_id.account_type == 'asset_receivable')):
            (receivable_accounts_line + line).with_context(move_reverse_cancel=True).reconcile()
        message_body_invoice = Markup("""
            <p>This invoice has a yield account entry created: <a href="#" data-oe-model="account.move"
            data-oe-id="{account_entry_id}">{account_entry_display_name}</a>""").format(
            account_entry_id=account_entry.id,
            account_entry_display_name=account_entry.display_name
        )
        move.message_post(body=message_body_invoice, subtype_xmlid="mail.mt_note")
        move.l10n_cl_aec_entry_ids = [Command.link(account_entry.id)]
        return account_entry

    def create_aec(self):
        moves = self.env['account.move'].browse(self._context.get('active_ids'))
        new_moves = []
        for move in moves:
            new_moves.append(self._l10n_cl_create_aec(move, self.partner_id, self.invoice_date_due))
        return new_moves
