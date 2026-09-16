from odoo import api, fields, models

FOLDER_DOMAIN = (
    "[('type', '=', 'folder'), ('shortcut_document_id', '=', False),"
    " '|', ('company_id', '=', False), ('company_id', '=', company_id)]"
)


class ResourceAssetKindDocument(models.Model):
    _name = "resource.asset.kind.document"
    _description = "Asset Kind Documents"
    _rec_name = "kind_id"

    kind_id = fields.Many2one(
        comodel_name="resource.asset.kind",
        index=True,
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        index=True,
        required=True,
    )
    centralize = fields.Boolean(
        string="Centralize Documents",
        default=True,
        help="File the documents of this kind of asset in the folder below.",
    )
    folder_id = fields.Many2one(
        comodel_name="document.document",
        string="Folder",
        compute="_compute_folder_id",
        store=True,
        readonly=False,
        domain=FOLDER_DOMAIN,
        check_company=True,
    )
    tag_ids = fields.Many2many(
        comodel_name="document.tag",
        string="Tags",
    )

    _kind_company_uniq = models.Constraint(
        "UNIQUE(kind_id, company_id)",
        "A kind of asset files its documents in one folder per company.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        settings = super().create(vals_list)
        settings._invalidate_assets()
        return settings

    def write(self, vals):
        result = super().write(vals)
        self._invalidate_assets()
        return result

    def unlink(self):
        result = super().unlink()
        self._invalidate_assets()
        return result

    def _invalidate_assets(self):
        # Assets read their folder off this row, and other models relay that
        # read; nothing declares either as a field dependency, so a change here
        # drops the caches wholesale. Settings move rarely.
        self.env.invalidate_all()

    @api.depends("kind_id", "company_id")
    def _compute_folder_id(self):
        for setting in self:
            if setting.folder_id:
                continue
            setting.folder_id = setting._find_or_create_folder()

    def _find_or_create_folder(self):
        self.check_singleton()
        documents = self.env["document.document"].sudo()
        name = self.kind_id.name
        existing = documents.search(
            [
                ("type", "=", "folder"),
                ("name", "=", name),
                ("company_id", "in", (False, self.company_id.id)),
            ],
            limit=1,
        )
        if existing:
            return existing
        return documents.create(
            {
                "name": name,
                "type": "folder",
                "company_id": self.company_id.id,
                "access_internal": "view",
                "access_via_link": "none",
            }
        )
