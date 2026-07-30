from odoo import api, fields, models

class ChangeState(models.TransientModel):
    _name = 'change.state'
    _description = 'Change State Wizard'


    property_id = fields.Many2one('property', string='Property', required=True)
    state = fields.Selection([
        ('new', 'New'),
        ('offer_received', 'Offer Received'),
    ], string='New State', required=True)
    reason = fields.Char(string='Reason for Change', required=True)

    def action_confirm(self):
        if self.property_id.state == 'closed':
            self.property_id.state = self.state
            self.property_id.create_history_record('closed', self.state, self.reason)

    # @api.multi
    # def change_state(self):
    #     active_ids = self.env.context.get('active_ids', [])
    #     properties = self.env['real.estate.property'].browse(active_ids)
    #     properties.write({'state': self.state})