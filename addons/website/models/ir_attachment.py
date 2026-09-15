import logging

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    key = fields.Char()
    website_id = fields.Many2one(comodel_name="website")

    @api.model_create_multi
    def create(self, vals_list):
        website = self.env["website"].get_current_website(fallback=False)
        for vals in vals_list:
            if (
                website
                and "website_id" not in vals
                and "not_force_website_id" not in self.env.context
            ):
                vals["website_id"] = website.id
        _debug.lifecycle(
            "attachment_website_defaulted",
            website=website.id if website else None,
            count=len(vals_list),
        )
        return super().create(vals_list)

    @api.model
    def get_groups_allowed_to_serve(self):
        return super().get_groups_allowed_to_serve() + [
            "website.group_website_designer"
        ]

    def _get_serve_attachment(self, url, extra_domain=None, order=None):
        website = self.env["website"].get_current_website()
        extra_domain = Domain(extra_domain or []) & website.website_domain()
        order = ("website_id, %s" % order) if order else "website_id"
        return super()._get_serve_attachment(url, extra_domain, order)
