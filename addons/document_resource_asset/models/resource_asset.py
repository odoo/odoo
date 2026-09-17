from odoo import Command, api, fields, models


class ResourceAsset(models.Model):
    _name = "resource.asset"
    _inherit = ["resource.asset", "mixin.documents"]

    document_ids = fields.One2many(
        comodel_name="document.document",
        inverse_name="res_id",
        string="Documents",
        domain=lambda self: [("res_model", "=", self._name)],
    )
    count_document = fields.Count(
        count_of="document_ids",
        string="Documents",
    )
    document_centralized = fields.Boolean(compute="_compute_document_centralized")

    @api.depends("kind_id", "company_id")
    def _compute_document_centralized(self):
        for asset in self:
            asset.document_centralized = asset._get_document_setting().centralize

    def _documents_company(self):
        return self.company_id or self.env.company

    def _get_document_setting(self):
        """The row naming where this kind of asset files its documents, in the
        asset's company. Kinds with no row file nothing."""
        self.check_singleton()
        if not self.kind_id:
            return self.env["resource.asset.kind.document"]
        return (
            self.env["resource.asset.kind.document"]
            .sudo()
            .search(
                [
                    ("kind_id", "=", self.kind_id.id),
                    ("company_id", "=", self._documents_company().id),
                ],
                limit=1,
            )
        )

    def _get_document_folder(self):
        return self._get_document_setting().folder_id

    def _get_document_tags(self):
        return self._get_document_setting().tag_ids

    def _get_document_owner(self):
        return self.env.user

    def _get_document_vals_access_rights(self):
        return {
            "access_internal": "view",
            "access_via_link": "none",
        }

    def _prepare_asset_document_vals(self, name, **extra):
        self.check_singleton()
        return {
            "name": name,
            "type": "binary",
            "res_model": self._name,
            "res_id": self.id,
            "folder_id": self._get_document_folder().id or False,
            "tag_ids": [Command.set(self._get_document_tags().ids)],
            "owner_id": self._get_document_owner().id,
            "company_id": self._documents_company().id,
            **self._get_document_vals_access_rights(),
            **extra,
        }

    def _file_document(self, name, **extra):
        return (
            self.env["document.document"]
            .sudo()
            .create(self._prepare_asset_document_vals(name, **extra))
            .with_env(self.env)
        )

    def _check_create_documents(self):
        return bool(
            self._get_document_setting().centralize
            and super()._check_create_documents()
        )

    def action_view_documents(self):
        self.check_singleton()
        if not self.document_centralized:
            return True
        folder = self._get_document_folder()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "document.document_action"
        )
        action["domain"] = [
            "|",
            ("type", "=", "folder"),
            "&",
            ("res_model", "=", self._name),
            ("res_id", "=", self.id),
        ]
        action["context"] = {
            "default_res_id": self.id,
            "default_res_model": self._name,
            "searchpanel_default_user_folder_id": str(folder.id) if folder else False,
            "searchpanel_default_tag_ids": self._get_document_tags().ids,
        }
        return action
