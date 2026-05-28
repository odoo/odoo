# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields
from odoo.addons.mail.tools.discuss import Store


class ResPartner(models.Model):
    _inherit = 'res.partner'

    leave_date_to = fields.Date(compute="_compute_leave_date_to")

    def _compute_leave_date_to(self):
        for partner in self:
            # in the rare case of multi-user partner, return the earliest
            # possible return date
            dates = partner.user_ids.mapped("leave_date_to")
            partner.leave_date_to = min(dates) if dates and all(dates) else False

    def _compute_im_status(self):
        super()._compute_im_status()
        absent_now = self._get_on_leave_ids()
        for partner in self:
            if partner.id in absent_now:
                if partner.im_status == 'online':
                    partner.im_status = 'leave_online'
                elif partner.im_status == 'away':
                    partner.im_status = 'leave_away'
                elif partner.im_status == 'busy':
                    partner.im_status = 'leave_busy'
                elif partner.im_status == 'offline':
                    partner.im_status = 'leave_offline'

    @api.model
    def _get_on_leave_ids(self):
        return self.env['res.users']._get_on_leave_ids(partner=True)

    def _store_partner_fields(self, res: Store.FieldList):
        super()._store_partner_fields(res)
        if res.is_for_internal_users():
            # sudo: access employee leave dates from other companies
            res.many(
                "employee_ids",
                ["active", "company_id", "leave_date_to", "user_id"],
                sudo=True,
            )
