from odoo import api, fields, models


class MailingMailing(models.Model):
    _inherit = 'mailing.mailing'

    @api.depends('card_campaign_id')
    def _compute_mailing_domain(self):
        # we consider if the card campaign is based on an (allowed) model, from the event module, that has an "event_id" field
        # it's always relevant to limit the domain to the related event
        card_event_mailings = self.filtered(
            lambda m: m.card_campaign_id and m.card_campaign_id.res_model in m.card_campaign_id._get_allowed_event_model_names()
        )
        # the event is only known through the domain, which the super call rebuilds from scratch
        previous_event_ids = {mailing.id: mailing._get_mailing_domain_event_id() for mailing in card_event_mailings}

        super()._compute_mailing_domain()

        for mailing in card_event_mailings:
            event_id = previous_event_ids[mailing.id]
            if not event_id:
                # sharing from the campaign, the record it was designed on is the only hint of an event
                preview_record = mailing.card_campaign_id.preview_record_ref
                event_id = preview_record.event_id.id if preview_record and 'event_id' in preview_record else False
            if not event_id:
                continue
            mailing_domain = fields.Domain(mailing._parse_mailing_domain())
            TargetModel = self.env[mailing.card_campaign_id.res_model]
            if not any(condition.field_expr == 'event_id' for condition in mailing_domain.iter_conditions()):
                final_domain = fields.Domain('event_id', '=', event_id) & mailing_domain
            else:
                # only support explicit '=' or 'in', if the condition is more complex nothing happens
                # it is assumed the user knows what they are doing
                final_domain = mailing_domain.optimize(TargetModel).map_conditions(
                    lambda condition: (
                        fields.Domain('event_id', '=', event_id)
                        if condition.field_expr == 'event_id' and condition.operator == 'in'
                        else condition
                    )
                ).optimize(TargetModel)
            mailing.mailing_domain = repr(final_domain)

    def _get_mailing_domain_event_id(self):
        """Return the event the mailing domain restricts to, if any.

        Only explicit '=' or 'in' conditions on a single event are supported,
        as those are the ones the domain is rebuilt with.
        """
        self.ensure_one()
        for condition in fields.Domain(self._parse_mailing_domain()).iter_conditions():
            if condition.field_expr != 'event_id':
                continue
            if condition.operator == '=' and isinstance(condition.value, int):
                return condition.value
            if condition.operator == 'in' and isinstance(condition.value, (list, tuple)) and len(condition.value) == 1:
                return condition.value[0]
        return False
