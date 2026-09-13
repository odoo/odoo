from odoo import fields, models

from .mixin_catalog import no_name_uniq_index


class ResPartnerTag(models.Model):
    _name = "res.partner.tag"
    _description = "Partner Tag"
    _inherit = ["mixin.tag.nested"]

    _name_src_uniq = no_name_uniq_index()

    parent_id: ResPartnerTag = fields.Many2one(
        comodel_name="res.partner.tag",
        string="Parent Tag",
        index=True,
        ondelete="cascade",
    )
    child_ids: ResPartnerTag = fields.One2many(
        comodel_name="res.partner.tag",
        inverse_name="parent_id",
        string="Child Tags",
    )
    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        column1="tag_id",
        column2="partner_id",
        string="Partners",
        copy=False,
    )
