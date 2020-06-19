import collections
import logging

from odoo import models
from odoo.tools import populate

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = "res.company"

    _populate_sizes = {
        'small': 5,
        'medium': 10,
        'large': 50,
    }

    def _populate_factories(self):
        # remaining: paperformat_id, parent_id, partner_id, favicon, font, report_header, external_report_layout_id, report_footer
        ref = self.env.ref
        def get_name(values=None, counter=0, **kwargs):
            return 'company_%s_%s' % (counter, self.env['res.currency'].browse(values['currency_id']).name)
        return [
            ('name', populate.constant('company_{counter}')),
            ('sequence', populate.randint(0, 100)),
            ('company_registry', populate.iterate([False, 'company_registry_{counter}'])),
            ('base_onboarding_company_state', populate.iterate(
                [False] + [e[0] for e in type(self).base_onboarding_company_state.selection])),
            ('primary_color', populate.iterate([False, '', '#ff7755'])),
            ('secondary_color', populate.iterate([False, '', '#ffff55'], seed='primary_color')),
            ('currency_id', populate.iterate([ref('base.EUR').id, ref('base.USD').id, ref('base.CHF').id, ref('base.CHF').id])),  # add more?
            ('name', populate.compute(get_name)),
        ]

    def _populate(self, size):
        records = super()._populate(size)
        self.env.ref('base.user_admin').write({'company_ids': [(4, rec.id) for rec in records]})  # add all created companies on user admin
        return records
