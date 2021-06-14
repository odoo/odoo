# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    original_expense_id = fields.Many2one('hr.expense')

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            res_model = values.get('res_model', self.env.context.get('default_res_model'))
            res_id = values.get('res_id', self.env.context.get('default_res_id'))
            if res_model == 'hr.expense' and res_id:
                expense_id = self.env['hr.expense'].browse(res_id)
                if expense_id.sheet_id:
                    self.env['ir.attachment'].create({
                        **values,
                        'res_model': 'hr.expense.sheet',
                        'res_id': expense_id.sheet_id.id,
                        'original_expense_id': res_id,
                    })

        return super().create(vals_list)

    def unlink(self):
        expense_ids = self.filtered(lambda a: a.res_model == 'hr.expense').mapped('res_id')
        if expense_ids:
            self.env['ir.attachment'].search([
                ('res_model', '=', 'hr.expense.sheet'),
                ('original_expense_id', 'in', expense_ids),
                ('name', 'in', self.mapped('name')),
            ]).unlink()

        return super().unlink()
