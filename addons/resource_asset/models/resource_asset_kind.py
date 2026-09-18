from odoo import fields, models


class ResourceAssetKind(models.Model):
    _name = "resource.asset.kind"
    _description = "Asset Kind"
    _inherit = ["mixin.catalog"]
    _order = "sequence, name, id"

    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    scheduled = fields.Boolean(
        help="Assets of this kind run on a shift and take their company's working hours; otherwise they are available around the clock."
    )
    identifier_type_ids = fields.Many2many(
        comodel_name="resource.asset.identifier.type",
        relation="resource_asset_kind_identifier_type_rel",
        column1="kind_id",
        column2="type_id",
        string="Required Identifiers",
        help="What an asset of this kind is expected to carry. A gap is reported on the asset; it refuses the asset only where the kind enforces it.",
    )
    enforce_identifiers = fields.Boolean(
        string="Refuse Incomplete Assets",
        help="Refuse an asset of this kind that is missing a required identifier, instead of only reporting the gap. Off by default: a unit usually arrives before its paperwork, and a fleet that is already incomplete would become unwritable.",
    )
    asset_properties_definition = fields.PropertiesDefinition(string="Asset Properties")
    asset_ids = fields.One2many(
        comodel_name="resource.asset",
        inverse_name="kind_id",
    )
    asset_count = fields.Count(count_of="asset_ids")

    _code_uniq = models.Constraint(
        "UNIQUE(code)", "Each asset kind code must be unique."
    )
