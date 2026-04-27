from odoo import models, fields, _


class OperationMode(models.Model):
    _name = 'l10n_co_dian.operation_mode'
    _description = "Colombian operation modes of DIAN used for different documents"

    dian_software_id = fields.Char(
        string="Software ID",
        required=True,
        help="Software identifier provided by the DIAN to invoice electronically with its own software",
    )
    dian_software_operation_mode = fields.Selection(
        string="Software Mode",
        selection=[
            ('invoice', "DIAN 2.1: Electronic Invoices"),
            ('bill', "DIAN 2.1: Support Documents")
        ],
        required=True,
        help="Select the type of document to be generated with the operation type configured",
    )
    dian_software_security_code = fields.Char(
        string="Software PIN",
        required=True,
        help="Software PIN created in the DIAN portal to invoice electronically with its own software",
    )
    dian_testing_id = fields.Char(
        string="Testing ID",
        help="Testing ID is needed for the certification process with the DIAN and for general testing of electronic invoicing workflows",
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        ondelete='cascade',
    )

    _sql_constraints = [
        ('uniq_software_operation_mode', 'UNIQUE(dian_software_operation_mode, company_id)', 'You cannot have two records with same mode'),
    ]

    def _compute_display_name(self):
        self.display_name = _("DIAN Operation Mode")
