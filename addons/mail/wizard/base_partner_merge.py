# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, _


class MergePartnerAutomatic(models.TransientModel):

    _inherit = 'base.partner.merge.automatic.wizard'

    @api.multi
    def _log_merge_operation(self, src_partners, dst_partner):
        super(MergePartnerAutomatic, self)._log_merge_operation(src_partners, dst_partner)
        dst_partner.message_post(body='%s %s' % (_("Merged with the following partners:"), ", ".join('%s <%s> (ID %s)' % (p.name, p.email or 'n/a', p.id) for p in src_partners)))
