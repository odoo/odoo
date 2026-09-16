# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.fields import Domain


class MailCallLogMixin(models.AbstractModel):
    """ Mail Call Log Mixin is a mixin class to use on a model the "Log Activity in
    Chatter" wizard offers to log a call on (see `mail.activity.schedule.call`):
    searching it, while a call is being logged, ranks the closest records first. """
    _name = 'mail.call.log.mixin'
    _description = 'Call Log Mixin'

    @api.model
    def name_search(self, name='', domain=None, operator='ilike', limit=100):
        """ When logging a call, offer the records about whoever attended it first, then
        those about their family, and only then the rest: the closer a record is to the
        call, the likelier the user is after it. """
        tiers = self._get_call_log_priority_domains()
        if not tiers:
            return super().name_search(name, domain, operator, limit)
        domain = Domain(domain if domain is not None else Domain.TRUE)
        matched = []
        # everything a previous tier offered, which the next ones must not offer again:
        # a record may well be about one partner of a tier and about another of the next
        offered = Domain.FALSE
        for tier in (*tiers, Domain.TRUE):
            if limit and len(matched) >= limit:
                break
            matched += super().name_search(
                name, domain & tier & ~offered, operator, limit and limit - len(matched),
            )
            offered |= tier
        return matched

    @api.model
    def _get_call_log_priority_domains(self):
        """ The tiers of records to offer, most relevant first, empty when no call is
        being logged. A tier matching nothing is left out, so that a model about no
        partner at all keeps its own order. """
        if 'log_channel_partner_ids' not in self.env.context:
            return []
        return [
            domain
            for partners in self.env['res.partner']._get_call_log_partner_tiers()
            if not (domain := self._get_call_log_partner_domain(partners)).is_false()
        ]

    @api.model
    def _get_call_log_partner_domain(self, partners):
        """ The records about one of the given partners, ``FALSE`` when the model is
        about no partner at all. """
        return Domain.OR(
            Domain(fname, 'in', partners.ids)
            for fname in self._mail_get_partner_fields()
        )
