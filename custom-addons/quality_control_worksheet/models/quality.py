# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from ast import literal_eval

from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.osv import expression


class QualityPoint(models.Model):
    _inherit = "quality.point"

    worksheet_template_id = fields.Many2one(
        'worksheet.template', 'Template',
        domain="[('res_model', '=', 'quality.check'), '|', ('company_ids', '=', False), ('company_ids', 'in', company_id)]")
    # tech field used by quality_field_domain widget
    worksheet_model_name = fields.Char(
        'Model Name', related='worksheet_template_id.model_id.model', readonly=True, store=True)
    worksheet_success_conditions = fields.Char('Success Conditions')


class QualityCheck(models.Model):
    _inherit = "quality.check"

    worksheet_template_id = fields.Many2one(
        'worksheet.template', 'Quality Template',
        domain="[('res_model', '=', 'quality.check'), '|', ('company_ids', '=', False), ('company_ids', 'in', company_id)]")
    worksheet_count = fields.Integer(compute='_compute_worksheet_count')

    @api.onchange('point_id')
    def _onchange_point_id(self):
        super()._onchange_point_id()
        if self.point_id and self.point_id.test_type == 'worksheet':
            self.worksheet_template_id = self.point_id.worksheet_template_id

    @api.depends('worksheet_template_id')
    def _compute_worksheet_count(self):
        for rec in self:
            rec.worksheet_count = rec.worksheet_template_id and rec.env[rec.worksheet_template_id.model_id.sudo().model].search_count([('x_quality_check_id', '=', rec.id)]) or 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'point_id' in vals and not vals.get('worksheet_template_id'):
                point = self.env['quality.point'].browse(vals['point_id'])
                if point.test_type == 'worksheet':
                    vals['worksheet_template_id'] = point.worksheet_template_id.id
        return super().create(vals_list)

    def action_open_quality_check_wizard(self, current_check_id=None):
        check_ids = sorted(self.ids)
        check_id = self.browse(current_check_id or check_ids[0])
        if check_id.test_type == 'worksheet':
            # in this case the worksheet will pop up, while the wizard will be in the background
            # to prevent code duplication
            action = check_id.action_quality_worksheet()
            quality_wizard = self.env['quality.check.wizard'].create({
                'check_ids': check_ids,
                'current_check_id': check_id.id,
            })
            action['context'].update({
                'default_check_ids': check_ids,
                'default_current_check_id': check_id.id,
                'quality_wizard_id': quality_wizard.id,
                'from_failure_form': False,
            })
            return action
        return super().action_open_quality_check_wizard(current_check_id)

    def action_quality_worksheet(self):
        action = self.worksheet_template_id.action_id.sudo().read()[0]
        worksheet = self.env[self.worksheet_template_id.model_id.sudo().model].search([('x_quality_check_id', '=', self.id)])
        context = literal_eval(action.get('context', '{}'))
        action_name = self._get_check_action_name()
        action.update({
            'name': action_name,
            'res_id': worksheet.id if worksheet else False,
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                **context,
                'edit': True,
                'default_x_quality_check_id': self.id,
            },
        })
        return action

    def action_worksheet_check(self):
        self.ensure_one()
        if self.worksheet_count == 0:
            raise UserError(_("Please fill in the worksheet."))
        else:
            domain = literal_eval(self.point_id.worksheet_success_conditions or '[]')
            model = self.env[self.worksheet_template_id.model_id.model]
            quality_wizard_id = self.env.context.get('quality_wizard_id')
            if not quality_wizard_id:
                return {'type': 'ir.actions.act_window_close'}
            quality_wizard = self.env['quality.check.wizard'].browse(quality_wizard_id)
            if model.search(expression.AND([domain, [('x_quality_check_id', '=', self.id)]])):
                return quality_wizard.do_pass()
            else:
                # TODO: Write fail message ?
                return quality_wizard.do_fail()

    def action_worksheet_discard(self):
        quality_wizard_id = self.env.context.get('quality_wizard_id')
        if quality_wizard_id:
            quality_wizard = self.env['quality.check.wizard'].browse(quality_wizard_id)
            return quality_wizard.action_generate_previous_window()
        return {'type': 'ir.actions.act_window_close'}

    def action_generate_next_window(self):
        quality_wizard_id = self.env.context.get('quality_wizard_id')
        if quality_wizard_id:
            quality_wizard = self.env['quality.check.wizard'].browse(quality_wizard_id)
            return quality_wizard.action_generate_next_window()
        return {'type': 'ir.actions.act_window_close'}

    def _is_pass_fail_applicable(self):
        return self.test_type == 'worksheet' and True or super()._is_pass_fail_applicable()
