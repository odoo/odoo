# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import ValidationError


class IrCronTrigger(models.Model):
    _inherit = 'ir.cron.trigger'

    @api.constrains('cron_id')
    def _check_image_cron_is_not_already_triggered(self):
        """ Ensure that there is a maximum of one trigger at a time for `ir_cron_fetch_image`.

        This cron is triggered in an optimal way to retrieve fastly the images without blocking a
        worker for a long amount of time. It fetches images in multiples batches to allow other
        crons to run in between. The cron also schedules itself if there are remaining products to
        be processed or if it encounters errors like a rate limit reached, a ConnectionTimeout, or
        service unavailable. Multiple triggers at the same will trouble the rate limit management
        and/or errors handling. More information in `product_fetch_image_wizard.py`.

        :return: None
        :raise ValidationError: If the maximum number of coexisting triggers for
                                `ir_cron_fetch_image` is reached
        """
        ir_cron_fetch_image = self.env.ref(
            'product_images.ir_cron_fetch_image', raise_if_not_found=False
        )

        if ir_cron_fetch_image and self.cron_id.id != ir_cron_fetch_image.id:
            return

        cron_triggers_count = self.env['ir.cron.trigger'].search_count(
            [('cron_id', '=', ir_cron_fetch_image.id)]
        )
        # When the cron is automatically triggered, we must allow two triggers to exists at the same
        # time: the one that triggered the cron and the one that will schedule another cron run. We
        # check whether the cron was automatically triggered rather than manually triggered to cover
        # the case where the admin would create an ir.cron.trigger manually.
        max_coexisting_cron_triggers = 2 if self.env.context.get('automatically_triggered') else 1
        if cron_triggers_count > max_coexisting_cron_triggers:
            raise ValidationError(_("This action is already scheduled. Please try again later."))
