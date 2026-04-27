# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ServerActions(models.Model):
    """ Add WhatsApp option in server actions. """
    _name = 'ir.actions.server'
    _inherit = ['ir.actions.server']

    # force insert before followers option
    state = fields.Selection(selection_add=[
        ('whatsapp', 'Send WhatsApp'), ('followers',),
    ], ondelete={'whatsapp': 'cascade'})
    # WhatsApp
    wa_template_id = fields.Many2one(
        'whatsapp.template', 'WhatsApp Template',
        compute='_compute_wa_template_id',
        ondelete='restrict', readonly=False, store=True,
        domain="[('model_id', '=', model_id), ('status', '=', 'approved')]",
    )

    @api.depends('model_id', 'state')
    def _compute_wa_template_id(self):
        to_reset = self.filtered(
            lambda act: act.state != 'whatsapp' or (act.model_id != act.wa_template_id.model_id)
        )
        if to_reset:
            to_reset.wa_template_id = False

    def _run_action_whatsapp_multi(self, eval_context=None):
        if not self.wa_template_id or self._is_recompute():
            return False

        records = eval_context.get('records') or eval_context.get('record')
        if not records:
            return False

        self.env['whatsapp.composer'].create({
            'res_ids': records.ids,
            'res_model': records._name,
            'wa_template_id': self.wa_template_id.id,
        })._send_whatsapp_template(force_send_by_cron=True)

        return False
