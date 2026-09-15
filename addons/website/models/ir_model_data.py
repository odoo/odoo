# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class IrModelData(models.Model):
    _inherit = 'ir.model.data'

    @api.model
    def _process_end_unlink_record(self, record):
        if record.env.context['module'].startswith('theme_'):
            theme_records = self.env['theme.engine']._theme_model_names.values()
            if record._name in theme_records:
                # use active_test to also unlink archived models
                copy_ids = record.with_context(active_test=False).copy_ids
                _logger.info('Deleting %s@%s (theme `copy_ids`) for website %s',
                             copy_ids.ids, record._name, copy_ids.mapped('website_id'))
                copy_ids.unlink()

        return super()._process_end_unlink_record(record)
