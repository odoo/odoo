# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailActivityMixin(models.AbstractModel):
    _inherit = "mail.activity.mixin"

    def _activity_schedule_postprocess(self, activities):
        super()._activity_schedule_postprocess(activities)
        call_pairs = [
            (record, activity)
            for record, activity in zip(self, activities)
            if activity.activity_category == "phonecall" and activity.phone
        ]
        partners_by_record = self.browse(
            [record.id for record, _activity in call_pairs]
        )._mail_get_partners()
        for record, activity in call_pairs:
            partners = partners_by_record[record.id]
            if (
                len(partners) == 1
                and partners.has_access("write")
                and not partners.phone
            ):
                partners.phone = activity.phone
