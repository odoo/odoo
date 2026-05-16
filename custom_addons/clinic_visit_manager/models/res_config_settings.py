from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    clinic_default_doctor_name = fields.Char(
        string="Default Doctor",
        config_parameter="clinic_visit_manager.default_doctor_name",
    )
    clinic_default_consultation_fee = fields.Float(
        string="Default Consultation Fee",
        config_parameter="clinic_visit_manager.default_consultation_fee",
    )
    clinic_auto_create_patient = fields.Boolean(
        string="Auto-create Patient Cards",
        config_parameter="clinic_visit_manager.auto_create_patient",
    )
    clinic_invoice_product_id = fields.Many2one(
        "product.product",
        string="Invoice Product",
        config_parameter="clinic_visit_manager.invoice_product_id",
        domain=[("sale_ok", "=", True)],
    )
