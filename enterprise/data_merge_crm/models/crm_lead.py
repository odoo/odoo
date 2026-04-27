# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = 'crm.lead'
    # As this model has its own data merge, avoid to enable the generic data_merge on that model.
    _disable_data_merge = True

    def _merge_method(self, destination, source):
        records = destination + source
        opp_ids = records.filtered(lambda opp: opp.probability < 100)
        if len(opp_ids) <= 1 and records:
            raise UserError(_('Won opportunities cannot be merged.'))

        merge_opp = opp_ids.merge_opportunity(auto_unlink=False)

        return {
            'records_merged': len(opp_ids),
            'log_chatter': False,
            'post_merge': True,
        }

    def _elect_master(self, records):
        return records._sort_by_confidence_level(reverse=True)[0]
