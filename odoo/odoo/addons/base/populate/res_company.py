import collections
import logging

from odoo import models, Command
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
        # Activate currency to avoid fail iterator
        (self.env.ref('base.USD') | self.env.ref('base.EUR')).active = True
        last_id = self.env["res.company"].search([], order="id desc", limit=1).id

        # remaining: paperformat_id, parent_id, partner_id, font, report_header, external_report_layout_id, report_footer
        def get_name(values=None, counter=0, **kwargs):
            return 'company_%s_%s' % (last_id + counter + 1, self.env['res.currency'].browse(values['currency_id']).name)

        active_currencies = self.env['res.currency'].search([('active', '=', True)]).ids
        return [
            ('name', populate.constant('company_{counter}')),
            ('sequence', populate.randint(0, 100)),
            ('company_registry', populate.iterate([False, 'company_registry_{counter}'])),
            ('primary_color', populate.iterate([False, '', '#ff7755'])),
            ('secondary_color', populate.iterate([False, '', '#ffff55'], seed='primary_color')),
            ('currency_id', populate.iterate(active_currencies)),
            ('name', populate.compute(get_name)),
        ]

    def _populate(self, size):
        records = super()._populate(size)
        self.env.ref('base.user_admin').write({'company_ids': [Command.link(rec.id) for rec in records]})  # add all created companies on user admin
        return records
