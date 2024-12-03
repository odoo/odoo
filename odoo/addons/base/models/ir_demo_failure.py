from odoo import api, fields, models


class IrDemo_Failure(models.TransientModel):
    """ Stores modules for which we could not install demo data
    """
    _name = 'ir.demo_failure'
    _description = 'Demo failure'

    module_id = fields.Many2one('ir.module.module', required=True, string="Module")
    error = fields.Char(string="Error")
    wizard_id = fields.Many2one('ir.demo_failure.wizard')


class IrDemo_FailureWizard(models.TransientModel):
    _name = 'ir.demo_failure.wizard'
    _description = 'Demo Failure wizard'

    failure_ids = fields.One2many(
        'ir.demo_failure', 'wizard_id', readonly=True,
        string="Demo Installation Failures"
    )
    failures_count = fields.Integer(compute='_compute_failures_count')

    @api.depends('failure_ids')
    def _compute_failures_count(self):
        for r in self:
            r.failures_count = len(r.failure_ids)

    def done(self):
        # pylint: disable=next-method-called
        return self.env['ir.module.module'].next()
