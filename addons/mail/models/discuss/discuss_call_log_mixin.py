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
        domain = Domain('display_name', operator, name) & Domain(domain or Domain.TRUE)
        # one part per tier, a record of several tiers belonging to the closest one, and
        # then the rest; each part keeps the order of the model and its own limit, so
        # that an index supporting that order remains usable
        parts = [tier & ~Domain.OR(tiers[:rank]) for rank, tier in enumerate(tiers)]
        parts.append(~Domain.OR(tiers))
        selects = []
        for seq, part in enumerate(parts):
            query = self._search(domain & part, limit=limit or None, order=self._order)
            if query.is_empty():
                continue
            selects.append(SQL("(%s)", query.select(
                query.table.id,
                SQL("%s AS seq", seq),
                SQL("row_number() OVER (ORDER BY %s) AS pos", query.order),
            )))
        if not selects:
            return []
        rows = self.env.execute_query(SQL(
            "SELECT id FROM (%s) AS parts ORDER BY seq, pos%s",
            SQL(" UNION ALL ").join(selects),
            SQL(" LIMIT %s", limit) if limit else SQL(),
        ))
        records = self.browse(id_ for id_, in rows)
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
