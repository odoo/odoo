# -*- coding: utf-8 -*-

from datetime import datetime
from odoo.tools.translate import _
from odoo import api, fields, models
from odoo.exceptions import UserError


class ApprovalWizard(models.TransientModel):
    _name = 'approval.wizard'
    _description = 'Approval Wizard'
    _inherit = ['mail.thread']

    module = model = fields.Many2one('ir.model', 'Transaction')
    current_stage = fields.Many2one('stage.master', 'Current Stage')
    new_stage = fields.Many2one('stage.master', 'New Stage')
    remark = fields.Text('Remark', required=True)
    current_stage_seq = fields.Integer('Sequence')
    new_stage_domain = fields.Char('New Stage Domain', help='Internal use only to set domain for new_stage.')

    @api.model
    def default_get(self, fields):
        compressed_list = []
        stage_list = []
        res = super(ApprovalWizard, self).default_get(fields)
        context = dict(self._context or {})
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')

        model_rec = self.env[active_model].browse(active_ids)
        for record in model_rec:
            model_id = self.env['ir.model'].search([('model', '=', active_model)])
            stage_list.append(record.stage_id.id)
            res.update({
                'current_stage': record.stage_id.id,
            })

        compressed_list = set(stage_list)
        if len(compressed_list) > 1:
            raise UserError(_('Please select records having same stage.'))

        return res

    @api.onchange('current_stage')
    def onchange_current_stage(self):
        context = dict(self._context or {})
        result = {}
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')

        model_rec = self.env[active_model].browse(active_ids)
        for record in model_rec:
            model_id = self.env['ir.model'].search([('model', '=', active_model)])
            stage_obj = self.env['stage.transaction'].search([('from_stage', '=', record.stage_id.id), ('model', '=', model_id.id)])
            stage_domain = [stage.to_stage.id for stage in stage_obj]

        return {
            'domain': {
                'new_stage': [('id', 'in', stage_domain)]
            }
        }

    def update_status(self):
        app_list = []
        data_lst = []
        context = dict(self._context or {})
        self.with_context(aprv=True)
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')
        app = self.env[active_model].browse(active_ids)

        if self.current_stage and self.new_stage:
            for approval in app:
                if self.new_stage.approved:
                    approval.stage_id = self.new_stage.id
                    vals = {
                        'date': datetime.now(),
                        'from_stage': self.current_stage.id,
                        'to_stage': self.new_stage.id,
                        'remark': self.remark,
                        'res_id': approval.id,
                        'model': active_model,
                    }
                    context.update({'copy': True})
                    approval.change_state(context)
                else:
                    approval.stage_id = self.new_stage.id
                    vals = {
                        'date': datetime.now(),
                        'from_stage': self.current_stage.id,
                        'to_stage': self.new_stage.id,
                        'remark': self.remark,
                        'res_id': approval.id,
                        'model': active_model,
                    }
                    context.update({'copy': False})
                    approval.change_state(context)

                self.env['mail.messages'].create(vals)
        else:
            raise UserError(_("Please select new_stage for transaction."))

    def reset_status(self):
        context = dict(self._context or {})
        stage_obj = self.env['stage.master'].search([('draft', '=', True)])
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')
        app = self.env[active_model].browse(active_ids)
        for approval in app:
            approval.stage_id = stage_obj.id
            vals = {
                'date': datetime.now(),
                'from_stage': self.current_stage.id,
                'to_stage': stage_obj.id,
                'remark': self.remark,
                'res_id': approval.id,
                'model': active_model,
            }
            self.env['mail.messages'].create(vals)

