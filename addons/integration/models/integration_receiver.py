from odoo import fields, models


class IntegrationReceiver(models.Model):
    _name = "integration.receiver"
    _inherit = ["mixin.integration.receiver"]
    _description = "Integration Receiver"
    _order = "sequence, id"

    res_model = fields.Char(
        string="Serves Model",
        index=True,
        readonly=True,
        help="The model of the record whose inbound calls this receiver admits.",
    )
    res_id = fields.Many2oneReference(
        model_field="res_model",
        string="Serves Record",
        index=True,
        readonly=True,
    )
    processing_mode = fields.Selection(default="sync")
    duplicate_detection_enabled = fields.Boolean(default=False)
