# coding: utf-8

from odoo import api, fields, models


class IrModule(models.Model):
    _name = 'ir.module.module'
    _inherit = 'ir.module.module'

    payment_environment = fields.Selection([
        ('test', 'Test'),
        ('prod', 'Production')], 'Acquirer Environment',
        compute='_compute_payment_environment', inverse='_set_payment_environment',
        search='_search_payment_environment')
    payment_acquirer_id = fields.Many2one(
        'payment.acquirer', compute='_compute_payment_acquirer_id')

    @api.depends('state')
    def _compute_payment_acquirer_id(self):
        payment_modules = self.filtered(lambda module: module.name.startswith('payment_'))
        payment_names = map(lambda name: name.split('payment_', 1)[1], payment_modules.mapped('name'))
        payment_acquirers = dict((acquirer.provider, acquirer.id) for acquirer in self.env['payment.acquirer'].search([('provider', 'in', payment_names)]))
        for module in payment_modules:
            module.payment_acquirer_id = payment_acquirers.get(module.name.split('payment_', 1)[1], False)

    @api.depends('payment_acquirer_id')
    def _compute_payment_environment(self):
        for module in self.filtered(lambda module: module.payment_acquirer_id):
            module.payment_environment = module.payment_acquirer_id.environment

    @api.multi
    def action_payment_immediate_install(self):
        if self.state != 'installed':
            self.button_immediate_install()
            context = dict(self._context, active_id=self.payment_acquirer_id.id)
            return {
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'payment.acquirer',
                'type': 'ir.actions.act_window',
                'res_id': self.payment_acquirer_id.id,
                'context': context,
            }

    @api.multi
    def action_payment_edit(self):
        context = dict(self._context, active_id=self.payment_acquirer_id.id)
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'payment.acquirer',
            'type': 'ir.actions.act_window',
            'res_id': self.payment_acquirer_id.id,
            'context': context,
        }
