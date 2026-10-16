from markupsafe import Markup, escape

from odoo import _, api, fields, models

from odoo.addons.l10n_fr_pdp.utils import transport_parties as parties


class PdpTransportConfirm(models.TransientModel):
    _name = 'l10n.fr.pdp.transport.confirm'
    _description = 'Peppol transport alert confirmation'

    move_ids = fields.Many2many('account.move', string='Invoices', readonly=True)
    alert_level = fields.Selection(
        selection=[
            (parties.LEVEL_WARNING, 'Warning'),
            (parties.LEVEL_CRITICAL, 'Critical'),
        ],
        compute='_compute_alert_level',
    )

    @api.depends('move_ids.l10n_fr_pdp_transport_alert_level')
    def _compute_alert_level(self):
        for wizard in self:
            levels = set(wizard.move_ids.mapped('l10n_fr_pdp_transport_alert_level'))
            wizard.alert_level = parties.LEVEL_CRITICAL if parties.LEVEL_CRITICAL in levels else parties.LEVEL_WARNING

    def action_confirm(self):
        self.ensure_one()
        moves = self.move_ids.filtered('l10n_fr_pdp_transport_needs_review')
        moves.write({
            'l10n_fr_pdp_transport_confirmed_uid': self.env.uid,
            'l10n_fr_pdp_transport_confirmed_date': fields.Datetime.now(),
            'to_check': False,
        })
        for move in moves:
            move.message_post(
                body=Markup('<b>%s</b> %s') % (
                    _("Peppol transport alert acknowledged by %(user)s.", user=self.env.user.name),
                    escape(move.l10n_fr_pdp_transport_alert_message or ''),
                ),
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
        return moves.action_post() or {'type': 'ir.actions.act_window_close'}
