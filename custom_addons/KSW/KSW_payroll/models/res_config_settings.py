from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ksw_gosi_rate = fields.Float(
        string='GOSI Rate (%)',
        help='Social insurance (GOSI) deduction percentage applied to '
             '(Basic + HRA) for Saudi employees.',
        config_parameter='ksw_payroll.gosi_rate',
        default=9.75,
    )

