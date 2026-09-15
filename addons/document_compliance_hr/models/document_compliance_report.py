from odoo import api, models


class DocumentComplianceReport(models.Model):
    _inherit = "document.compliance.report"

    @api.model
    def _get_entity_model_map(self) -> dict[str, str]:
        return {**super()._get_entity_model_map(), "hr.employee": "hr_employee"}
