# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.fields import Domain
from odoo.tools import SQL


class DiscussCallLogMixin(models.AbstractModel):
    """ Inherit this mixin on a business record a Discuss meeting can be logged on, so
    that "Log Activity in Chatter" (see `mail.activity.schedule.call`) lists the records
    of whoever was in that meeting before all the others.

    The ranking goes by tiers of partners, closest to the call first: its attendees,
    then their commercial partners, then the other contacts of those. A record sits in
    the tier of its own main partners (see `_get_call_log_partner_domain`).
    """
    _name = 'discuss.call.log.mixin'
    _description = 'Discuss Call Log Mixin'

    @api.model
    def name_search(self, name='', domain=None, operator='ilike', limit=100):
        """ Rank the records of the closest tier first, while a call is being logged. """
        tiers = self._get_call_log_priority_domains()
        if not tiers:
            return super().name_search(name, domain, operator, limit)
        query = self._search(Domain('display_name', operator, name) & Domain(domain or Domain.TRUE))
        if query.is_empty():
            return []
        # a single query ranks them all, a record of several tiers belonging to the
        # closest one, and then the rest in the order of the model
        query.order = SQL(
            "CASE %s ELSE %s END, %s",
            SQL(" ").join(
                SQL("WHEN %s THEN %s", tier.optimize_full(self)._to_sql(query.table), rank)
                for rank, tier in enumerate(tiers)
            ),
            len(tiers),
            self._order_to_sql(query.table, self._order),
        )
        query.limit = limit or None
        records = self.browse(id_ for id_, in self.env.execute_query(query.select()))
        return [(record.id, record.display_name) for record in records.sudo()]

    @api.model
    def _get_call_log_priority_domains(self):
        """ One domain per tier, closest first, empty when no call is being logged. A
        tier matching nothing is left out, so that a model about no partner at all keeps
        its own order. """
        if 'log_channel_partner_ids' not in self.env.context:
            return []
        return [
            domain
            for partners in self.env['res.partner']._get_call_log_partner_tiers()
            if not (domain := self._get_call_log_partner_domain(partners)).is_false()
        ]

    @api.model
    def _get_call_log_partner_domain(self, partners):
        """ The records whose main partners, the ones `_mail_get_partner_fields` points
        at, include one of ``partners``. ``FALSE`` when the model has no main partner at
        all. """
        return Domain.OR(
            Domain(fname, 'in', partners.ids)
            for fname in self._mail_get_partner_fields()
        )
