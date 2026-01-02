# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models
from odoo.exceptions import UserError


class BasePartnerMergeAutomaticWizard(models.TransientModel):
    _inherit = 'base.partner.merge.automatic.wizard'

    @api.model
    def _update_foreign_keys(self, src_partners, dst_partner):
        # check if the list of partners to merge have duplicate course
        courses_set = set(dst_partner.sudo().slide_channel_ids.ids)
        for partner in src_partners:
            for slide_channel in partner.sudo().slide_channel_ids:
                if slide_channel.id in courses_set:
                    raise UserError(self.env._("You cannot merge contacts that are enrolled in the same course."))
                courses_set.add(slide_channel.id)

        super()._update_foreign_keys(src_partners, dst_partner)
