# coding: utf-8

from odoo import api, fields, models


class IrModule(models.Model):
    _name = 'ir.module.module'
    _inherit = 'ir.module.module'

    # payment_environment = fields.Selection([
    #     ('test', 'Test'),
    #     ('prod', 'Production')], 'Acquirer Environment',
    #     compute='_compute_payment_environment', inverse='_set_payment_environment',
    #     search='_search_payment_environment')
    payment_acquirer_ids = fields.Many2many(
        'payment.acquirer', compute='_compute_payment_acquirer_info')
    payment_acquirer_data = fields.Text(
        compute='_compute_payment_acquirer_info')

    @api.depends('state')
    def _compute_payment_acquirer_info(self):
        payment_modules = self.filtered(lambda module: module.name.startswith('payment_'))
        payment_names = [module.name[8:] for module in payment_modules]
        payment_acquirers = dict((item, list()) for item in payment_names)
        for acquirer in self.env['payment.acquirer'].search([('provider', 'in', payment_names)]):
            payment_acquirers[acquirer.provider].append({
                'name': acquirer.name,
                'provider': acquirer.provider,
                'id': acquirer.id,
                'environment': acquirer.environment,
            })

        print payment_acquirers
        for module in payment_modules:
            module.payment_acquirer_ids = [item['id'] for item in payment_acquirers.get(module.name.split('payment_', 1)[1], dict())]
            print module, module.payment_acquirer_ids

        for module in payment_modules:
            module.payment_acquirer_data = payment_acquirers.get(module.name.split('payment_', 1)[1], False)
            print module, module.payment_acquirer_data

    # @api.depends('payment_acquirer_id')
    # def _compute_payment_environment(self):
    #     for module in self.filtered(lambda module: module.payment_acquirer_id):
    #         module.payment_environment = module.payment_acquirer_id.environment

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
