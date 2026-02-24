# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountInvoice(models.Model):
    _inherit = "account.move"
    _description = 'Account Invoice'

    @api.model
    def _default_stage(self):
        st_ids = self.env['stage.master'].search([('draft', '=', True)])
        if st_ids:
            for st_id in st_ids:
                return st_id.id

    retention_amt = fields.Float(string='Retention')
    credit_sum = fields.Float(string='Credit sum')
    recovery_sum = fields.Float(string='Recovery sum')
    ra_bill_invoice = fields.Boolean(string='RA Bill?')

    project_id = fields.Many2one('project.project', string='Project', required=False)
    project_wbs_id = fields.Many2one('project.task', string='Project WBS Name',
                                     domain=[('is_wbs', '=', True), ('project_id', '!=', False)], required=False)
    grn_ids = fields.Many2many('stock.picking', 'picking_invoice_rel', 'invoice_id', 'picking_id',
                               string="Picking Details")

    flag = fields.Boolean(string='Flag')

    mesge_ids = fields.One2many('mail.messages', 'res_id', string='Massage',
                                domain=lambda self: [('model', '=', self._name)], auto_join=True, readonly=True)

    stage_id = fields.Many2one('stage.master', 'Stage', default=_default_stage)

    """ OLD METHOD COMMENTED"""

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            existing_stage = []
            st_id = self.env['stage.master'].sudo().search([('draft', '=', True)])

            # invoice to move
            msg_ids = {
                'date': datetime.now(),
                'from_stage': None,
                'to_stage': st_id.id,
                'remark': 'Created by ' + str(self.env['res.users'].browse(self._uid).name),
                'model': 'account.move'
            }

            existing_stage.append((0, 0, msg_ids))
            vals.update({'mesge_ids': existing_stage})

        return super(AccountInvoice, self).create(vals_list)

    def change_state(self, context={}):
        if context.get('copy') == True:
            self.flag = True
        else:
            view_id = self.env.ref('pragtech_contracting.approval_wizard_form_view_contracting').id
            return {
                'type': 'ir.actions.act_window',
                'key2': 'client_action_multi',
                'res_model': 'approval.wizard',
                'multi': 'True',
                'target': 'new',
                'views': [[view_id, 'form']],
            }


class AccountMoveExtended(models.Model):
    _inherit = "account.move.line"

    def _prepare_analytic_distribution_line(self, distribution, account_id, distribution_on_each_plan):
        self.ensure_one()
        if account_id == 'false':
            raise ValidationError(_('Analytic Account Should Be Configure On The Project Master.'))
        else:
            return super(AccountMoveExtended, self)._prepare_analytic_distribution_line(distribution, account_id,
                                                                                        distribution_on_each_plan)
