# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, models
from odoo.http import request

_logger = logging.getLogger(__name__)


class IrModelData(models.Model):
    _inherit = 'ir.model.data'

    @api.model
    def _process_end_unlink_record(self, record):
        if record._context['module'].startswith('theme_'):
            theme_records = self.env['ir.module.module']._theme_model_names.values()
            if record._name in theme_records:
                # use active_test to also unlink archived models
                # and use MODULE_UNINSTALL_FLAG to also unlink inherited models
                copy_ids = record.with_context({
                    'active_test': False,
                    'MODULE_UNINSTALL_FLAG': True
                }).copy_ids
                if request:
                    # we are in a website context, see `write()` override of
                    # ir.module.module in website
                    current_website = self.env['website'].get_current_website()
                    copy_ids = copy_ids.filtered(lambda c: c.website_id == current_website)

                _logger.info('Deleting %s@%s (theme `copy_ids`) for website %s',
                             copy_ids.ids, record._name, copy_ids.website_id)
                copy_ids.unlink()

        return super()._process_end_unlink_record(record)
