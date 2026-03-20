# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools.misc import str2bool

from odoo.addons.sale import const


class IrConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'

    @api.model_create_multi
    def create(self, vals_list):
        configs = super().create(vals_list)
        configs._sale_sync_linked_crons()
        return configs

    def write(self, vals):
        res = super().write(vals)
        self._sale_sync_linked_crons()
        return res

    def unlink(self):
        self._sale_sync_linked_crons(unlink=True)
        return super().unlink()

    def _sale_sync_linked_crons(self, unlink=False):
        """Synchronize Sales-related crons' `active` field based on linked configuration parameters.

        :param bool unlink: Whether this sync is triggered by parameter deletion.
        :return: None
        """
        param_cron_mapping = self._get_param_cron_mapping()
        for config in self.filtered(lambda c: c.key in param_cron_mapping):
            linked_cron_xmlid = param_cron_mapping[config.key]
            if linked_cron := self.env.ref(linked_cron_xmlid, raise_if_not_found=False):
                linked_cron.active = False if unlink else str2bool(config.value)

    def _get_param_cron_mapping(self):
        """Return a mapping of config parameters to linked crons' XMLIDs.

        :return: The config-cron mapping.
        :rtype: dict
        """
        return const.PARAM_CRON_MAPPING
