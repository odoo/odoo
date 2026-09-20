from odoo import Command, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MixinDocuments(models.AbstractModel):
    _name = "mixin.documents"
    _inherit = "mixin.documents.unlink"
    _description = "Documents creation mixin"

    def _prepare_document_vals(self, attachment: models.Model) -> dict:
        self.check_singleton()
        document_vals = {}
        if self._check_create_documents():
            access_rights_vals = self._get_document_vals_access_rights()
            if set(access_rights_vals) - {
                "access_via_link",
                "access_internal",
                "is_access_via_link_hidden",
            }:
                _debug.logic(
                    "document_vals_refused",
                    model=self._name,
                    keys=sorted(access_rights_vals),
                )
                raise ValueError("Invalid access right values")

            owner = self._get_document_owner()
            folder = self._get_document_folder()
            document_vals = {
                "attachment_id": attachment.id,
                "name": attachment.name or self.display_name,
                "folder_id": folder.id,
                "company_id": folder.company_id.id,
                "owner_id": owner.id if owner.active else False,
                "partner_id": self._get_document_partner().id,
                "tag_ids": [(6, 0, self._get_document_tags().ids)],
            } | access_rights_vals
            _debug.pipeline(
                "document_vals_built",
                model=self._name,
                folder=folder,
                owner=owner,
                attachment=attachment,
                carries_attachment=bool(document_vals.get("attachment_id")),
            )
        return document_vals

    def _get_document_vals_access_rights(self) -> dict:
        return {
            "access_via_link": "none",
            "access_internal": "none",
            "is_access_via_link_hidden": True,
        }

    def _get_document_owner(self) -> models.Model:
        return self.env["res.users"]

    def _get_document_tags(self) -> models.Model:
        return self.env["document.tag"]

    def _get_document_folder(self) -> models.Model:
        return self.env["document.document"]

    def _get_document_partner(self) -> models.Model:
        return self.env["res.partner"]

    def _get_document_access_ids(self) -> list:
        return []

    def _check_create_documents(self) -> bool:
        return bool(self and self._get_document_folder())

    def _prepare_document_create_values_for_linked_records(
        self, res_model: str, vals_list: list[dict], pre_vals_list: list[dict]
    ) -> list[dict]:
        if self._get_reference_model_name() != res_model:
            _debug.logic(
                "linked_record_vals_refused", model=self._name, res_model=res_model
            )
            raise ValueError(f"Invalid model {res_model} (expected {self._name})")

        related_record_by_id = (
            self.env[res_model]
            .browse([res_id for vals in vals_list if (res_id := vals.get("res_id"))])
            .grouped("id")
        )
        for vals, pre_vals in zip(vals_list, pre_vals_list, strict=True):
            if not vals.get("res_id"):
                continue
            related_record = related_record_by_id.get(vals["res_id"])
            vals.update(
                {
                    "owner_id": pre_vals.get(
                        "owner_id", related_record._get_document_owner().id
                    ),
                    "partner_id": pre_vals.get(
                        "partner_id", related_record._get_document_partner().id
                    ),
                    "tag_ids": pre_vals.get(
                        "tag_ids", [(6, 0, related_record._get_document_tags().ids)]
                    ),
                }
                | {
                    key: value
                    for key, value in related_record._get_document_vals_access_rights().items()
                    if key not in pre_vals
                }
            )
            if "access_ids" in pre_vals:
                continue
            access_ids = vals.get("access_ids") or []
            partner_with_access = {
                access[2]["partner_id"] for access in access_ids if access[2]
            }
            access_ids.extend(
                Command.create(
                    {
                        "partner_id": partner.id,
                        "role": role,
                        "expiration_date": expiration_date,
                    }
                )
                for partner, (role, expiration_date) in (
                    related_record._get_document_access_ids()
                )
                if partner.id not in partner_with_access
            )
            vals["access_ids"] = access_ids
        _debug.pipeline(
            "linked_record_vals_prepared", res_model=res_model, count=len(vals_list)
        )
        return vals_list
