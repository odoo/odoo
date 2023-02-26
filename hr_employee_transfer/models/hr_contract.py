from odoo import models, fields, api


class HrContract(models.Model):
    _inherit = 'hr.contract'

    emp_transfer = fields.Many2one('employee.transfer',
                                   string='Transferred Employee',
                                   help="Transferred employee")

    @api.model
    def create(self, vals):
        res = super(HrContract, self).create(vals)
        if res.emp_transfer:
            res.emp_transfer.write(
                {'state': 'done'})
        return res
