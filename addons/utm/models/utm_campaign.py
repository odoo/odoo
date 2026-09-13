from odoo import api, fields, models


class UtmCampaign(models.Model):
    _name = "utm.campaign"
    _description = "UTM Campaign"
    _rec_name = "title"

    active = fields.Boolean(default=True)
    name = fields.Char(
        string="Campaign Identifier",
        translate=False,
        compute="_compute_name",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
    )
    title = fields.Char(
        string="Campaign Name",
        translate=True,
        required=True,
    )

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        default=lambda self: self.env.uid,
        required=True,
    )
    stage_id = fields.Many2one(
        comodel_name="utm.stage",
        default=lambda self: self.env["utm.stage"].search([], limit=1),
        copy=False,
        required=True,
        group_expand="_group_expand_stage_ids",
        ondelete="restrict",
    )
    tag_ids = fields.Many2many(
        comodel_name="utm.tag",
        relation="utm_tag_rel",
        column1="tag_id",
        column2="campaign_id",
        string="Tags",
    )

    is_auto_campaign = fields.Boolean(
        string="Automatically Generated Campaign",
        default=False,
        help="Allows us to filter relevant Campaigns",
    )
    color = fields.Integer(string="Color Index")

    _unique_name = models.Constraint(
        "UNIQUE(name)",
        "The name must be unique",
    )

    @api.depends("title")
    def _compute_name(self):
        new_names = (
            self.env["mixin.utm"]
            .with_context(utm_check_skip_record_ids=self.ids)
            ._get_unique_names(self._name, [c.title for c in self])
        )
        for campaign, new_name in zip(self, new_names, strict=True):
            campaign.name = new_name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("title") and vals.get("name"):
                vals["title"] = vals["name"]
        new_names = self.env["mixin.utm"]._get_unique_names(
            self._name, [vals.get("name") for vals in vals_list]
        )
        for vals, new_name in zip(vals_list, new_names, strict=True):
            if new_name:
                vals["name"] = new_name
        return super().create(vals_list)

    @api.model
    def _group_expand_stage_ids(self, stages, domain):
        """Read group customization in order to display all the stages in the
        Kanban view, even if they are empty.
        """
        stage_ids = stages.sudo()._search([], order=stages._order)
        return stages.browse(stage_ids)
