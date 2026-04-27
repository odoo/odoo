from odoo import api, fields, models, _

class l10nCHLPPEMA(models.Model):
    _name = "l10n.ch.lpp.mutation"
    _description = "BVG-LPP Mutations"
    _order = "valid_as_of desc"

    employee_snapshot_id = fields.Many2one("l10n.ch.employee.monthly.values")
    contract_id = fields.Many2one("hr.contract")
    employee_id = fields.Many2one("hr.employee")
    reason = fields.Selection(selection=[("changeSalary", "Salary Change"),
                                         ("activityRate", "Activity Rate Change"),
                                         ("changeBVG-LPP-Code", "LPP Code Change"),
                                         ("residence", "Residence Change"),
                                         ("civilstate", "Civil Status"),
                                         ("partialRetirement", "Partial Retirement"),
                                         ("others", "Other")], required=True)
    valid_as_of = fields.Date(required=True)
    auto_generated = fields.Boolean()
