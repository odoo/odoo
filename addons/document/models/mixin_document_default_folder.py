from odoo import models


class MixinDocumentDefaultFolder(models.AbstractModel):
    _name = "mixin.document.default.folder"
    _description = "Default document folder of a bridge module"

    def _reset_default_documents_folder_id(
        self,
        toggle_field_name: str,
        folder_field_name: str,
        default_folder_id: models.Model,
    ) -> None:
        if not default_folder_id or not default_folder_id.active:
            return
        bridge_enabling_records = self.filtered(toggle_field_name).filtered(
            lambda record: not record[folder_field_name]
        )
        bridge_enabling_records[folder_field_name] = default_folder_id
