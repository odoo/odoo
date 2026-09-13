from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MixinUtmSource(models.AbstractModel):
    """Mixin generating a source's name from its `_rec_name` content."""

    _name = "mixin.utm.source"
    _description = "UTM Source Mixin"

    name = fields.Char(
        related="source_id.name",
        string="Name",
        readonly=False,
    )
    source_id = fields.Many2one(
        comodel_name="utm.source",
        copy=False,
        required=True,
        ondelete="restrict",
    )

    @api.model
    def default_get(self, fields):
        # Exclude 'name' from fields to avoid retrieving it from context.
        return super().default_get([field for field in fields if field != "name"])

    @api.model_create_multi
    def create(self, vals_list):
        """Create the UTM sources if necessary, generate the name based on the content in batch."""
        # Create all required <utm.source>
        utm_sources = self.env["utm.source"].create(
            [
                {
                    "name": values.get("name")
                    or self.env.context.get("default_name")
                    or self.env["utm.source"]._generate_name(
                        self, values.get(self._rec_name)
                    ),
                }
                for values in vals_list
                if not values.get("source_id")
            ]
        )

        # Update "vals_list" to add the ID of the newly created source
        vals_list_missing_source = [
            values for values in vals_list if not values.get("source_id")
        ]
        # both are filtered/created by the same `not source_id` condition, so equal-length by construction
        for values, source in zip(vals_list_missing_source, utm_sources, strict=True):
            values["source_id"] = source.id

        for values in vals_list:
            if "name" in values:
                del values["name"]

        return super().create(vals_list)

    def write(self, vals):
        if (vals.get(self._rec_name) or vals.get("name")) and len(self) > 1:
            raise UserError(
                _(
                    "You cannot update multiple records with the same name. The name should be unique!"
                )
            )

        if vals.get(self._rec_name) and not vals.get("name"):
            vals["name"] = self.env["utm.source"]._generate_name(
                self, vals[self._rec_name]
            )
        if vals.get("name"):
            vals["name"] = (
                self.env["mixin.utm"]
                .with_context(utm_check_skip_record_ids=self.source_id.ids)
                ._get_unique_names("utm.source", [vals["name"]])[0]
            )

        return super().write(vals)

    def copy_data(self, default=None):
        """Increment the counter when duplicating the source."""
        default = default or {}
        default_name = default.get("name")
        vals_list = super().copy_data(default=default)
        # copy_data returns one vals dict per record (ORM contract), so self and vals_list align
        for source, vals in zip(self, vals_list, strict=True):
            vals["name"] = self.env["mixin.utm"]._get_unique_names(
                "utm.source", [default_name or source.name]
            )[0]
        return vals_list
