# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    def _has_recording_feature(self):
        return super()._has_recording_feature() or bool(self.env["res.config.settings"]._get_cloud_storage_configuration())
