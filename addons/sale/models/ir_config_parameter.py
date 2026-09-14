from odoo import api, models
from odoo.libs.debug_log import DebugLog
from odoo.tools.misc import str2bool

from odoo.addons.sale import const

_debug = DebugLog(__name__)


class IrConfigParameter(models.Model):
    _inherit = "ir.config_parameter"

    @api.model_create_multi
    def create(self, vals_list):
        configs = super().create(vals_list)
        _debug.lifecycle("create", params=configs, rows=len(vals_list))
        configs._sale_sync_linked_crons()
        return configs

    def write(self, vals):
        res = super().write(vals)
        _debug.lifecycle("write", params=self, fields=list(vals))
        self._sale_sync_linked_crons()
        return res

    def unlink(self):
        _debug.lifecycle("unlink", params=self)
        self._sale_sync_linked_crons(unlink=True)
        return super().unlink()

    def _sale_sync_linked_crons(self, unlink=False):
        param_cron_mapping = self._get_param_cron_mapping()
        for config in self.filtered(lambda c: c.key in param_cron_mapping):
            linked_cron_xmlid = param_cron_mapping[config.key]
            if linked_cron := self.env.ref(linked_cron_xmlid, raise_if_not_found=False):
                linked_cron.active = False if unlink else str2bool(config.value)
                _debug.lifecycle(
                    "linked_cron_synced",
                    param=config.key,
                    cron=linked_cron_xmlid,
                    active=linked_cron.active,
                )

    def _get_param_cron_mapping(self):
        return const.PARAM_CRON_MAPPING
