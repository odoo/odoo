from odoo import models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    def _generate_and_send_invoices(self, moves, from_cron=False, allow_raising=True, allow_fallback_pdf=False, **custom_settings):
        # EXTENDS 'account' - to create the pdf attachment
        # in the matching inter-company move
        res = super()._generate_and_send_invoices(moves, from_cron=from_cron, allow_raising=allow_raising, allow_fallback_pdf=allow_fallback_pdf, **custom_settings)

        partner_companies = self.env['res.company'].sudo().search([]).partner_id.ids

        moves_with_attachments = moves.filtered(
            lambda move: bool(move.message_main_attachment_id)
            and move.is_sale_document(include_receipts=True)
            and move.commercial_partner_id.id in partner_companies
        )

        ico_moves = self.env['account.move'].sudo().search([
            ('move_type', 'in', self.env['account.move'].get_purchase_types(include_receipts=True)),
            ('auto_generated', '=', True),
            ('auto_invoice_id', 'in', moves_with_attachments.ids)
        ])

        for ico_move in ico_moves:
            original_move = ico_move.auto_invoice_id
            move_attachment = original_move.message_main_attachment_id
            if not move_attachment:  # shouldn't happen but just in case
                continue

            ico_move.message_main_attachment_id = self.env['ir.attachment']\
                .with_user(ico_move.company_id.intercompany_user_id.id).with_company(ico_move.company_id.id).create({
                    'name': f'{original_move.name}.pdf',
                    'type': 'binary',
                    'mimetype': 'application/pdf',
                    'raw': move_attachment.raw,
                    'res_model': 'account.move',
                    'res_id': ico_move.id,
                })

        return res
