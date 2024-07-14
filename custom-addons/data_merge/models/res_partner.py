# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

import datetime


class Partner(models.Model):
    _inherit = 'res.partner'
    # As this model has his own data merge, avoid to enable the generic data_merge on that model.
    _disable_data_merge = True

    def _merge_method(self, destination, source):
        source = source if source else self.env['res.partner']
        wizard = self.env['base.partner.merge.automatic.wizard'].with_context({
            'active_ids': [destination.id] + source.ids,
            'active_model': 'res.partner'
        }).create({'dst_partner_id': destination.id})
        wizard.action_merge()

        return {
            'records_merged': len(source) + 1,
            'log_chatter': True,
            'post_merge': False,
        }

    def _elect_method(self, records):
        return records.sorted(
            key=lambda p: (not p.active, (p.create_date or datetime.datetime(1970, 1, 1))),
        )[:1]
