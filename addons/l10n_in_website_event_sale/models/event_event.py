from odoo import api, fields, models

class EventEvent(models.Model):
    """Event"""
    _inherit = ['event.event']

    country_code = fields.Char(related='company_id.country_code')
    l10n_in_state_id = fields.Many2one('res.country.state', string="Place of supply",
        compute="_compute_l10n_in_event_state_id", store=True, copy=True, readonly=False)
    l10n_in_pos_treatment = fields.Selection([('always', 'Always'),
                                              ('for_unregistered', 'For Unregistered'),
                                             ], default='always', required=True)

    @api.depends('address_id', 'country_code')
    def _compute_l10n_in_event_state_id(self):
        for event in self:
            event.l10n_in_state_id = False
            if event.country_code == 'IN':
                event.l10n_in_state_id = event.address_id.state_id if event.address_id.country_code == 'IN' else self.env.ref('l10n_in.state_in_oc', raise_if_not_found=False)
