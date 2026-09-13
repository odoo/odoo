import logging

from odoo import fields, models
from odoo.http import request

logger = logging.getLogger(__name__)


class MixinWebsiteMulti(models.AbstractModel):
    _name = "mixin.website.multi"

    _description = "Multi Website Mixin"

    website_id = fields.Many2one(
        comodel_name="website",
        index=True,
        ondelete="restrict",
        help="Restrict to a specific website.",
    )

    def can_access_from_current_website(self, website_id=False):
        can_access = True
        for record in self:
            if (website_id or record.website_id.id) not in (
                False,
                request.env["website"].get_current_website().id,
            ):
                can_access = False
                continue
        return can_access
