from odoo import api, models

KIND_SCOPE = """
    e.entity_type != 'resource.asset'
    OR NOT EXISTS (
        SELECT 1 FROM document_type_resource_asset_kind_rel r
         WHERE r.type_id = dt.id
    )
    OR EXISTS (
        SELECT 1
          FROM document_type_resource_asset_kind_rel r
          JOIN resource_asset asset ON asset.id = e.entity_id
         WHERE r.type_id = dt.id
           AND r.kind_id = asset.kind_id
    )
"""


class DocumentComplianceReport(models.Model):
    _inherit = "document.compliance.report"

    @api.model
    def _get_entity_model_map(self) -> dict[str, str]:
        return {**super()._get_entity_model_map(), "resource.asset": "resource_asset"}

    def _get_type_scope_conditions(self) -> list[str]:
        # A type naming no kind keeps applying to every asset, so this narrows
        # only the types that asked to be narrowed.
        return [*super()._get_type_scope_conditions(), KIND_SCOPE]
