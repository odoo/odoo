# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, modules


class EventLeadRequest(models.Model):
    """ Technical model created when a user requests 'leads generation' on an event based on all
    existing event.lead.rules (see event#action_generate_leads).

    As an event can hold a lot of registrations, we use a batch approach with a separate model that
    contains the batching logic method and the field to retain progress.

    To benefit from a background processing, we use a CRON that calls itself with a CRON trigger
    until the batch is completed, which unlinks this technical generation record. """

    _name = 'event.lead.request'
    _description = "Event Lead Request"
    _log_access = False
    _rec_name = "event_id"
    _order = "id asc"

    _REGISTRATIONS_BATCH_SIZE = 200

    event_id = fields.Many2one('event.event', required=True, string="Event", ondelete="cascade")
    event_lead_rule_ids = fields.Many2many('event.lead.rule', string="Lead Rules")
    processed_registration_id = fields.Integer("Processed Registration",
        help="The ID of the last processed event.registration, used to know where to resume.")

    _uniq_event = models.Constraint(
        'unique(event_id)',
        'You can only have one generation request per event at a time.',
    )

    @api.model
    def _cron_generate_leads(self, job_limit=100, registrations_batch_size=None):
        """ See class docstring for details.

        :param job_limit: The maximum amount of 'event.lead.request' to process
          Defaults to 100.
        :param registrations_batch_size: The amount of attendees processed at once.
          Defaults to event.lead.request._REGISTRATIONS_BATCH_SIZE """

        # auto-commit except in testing mode
        auto_commit = not modules.module.current_test

        registrations_batch_size = registrations_batch_size or self._REGISTRATIONS_BATCH_SIZE
        generate_requests = self.env['event.lead.request'].search([], limit=job_limit)
        fulfilled_requests = self.env['event.lead.request']
        for generate_request in generate_requests:
            registrations_to_process = self.env['event.registration'].search([
                ('event_id', '=', generate_request.event_id.id),
                ('state', 'not in', ['draft', 'cancel']),
                ('id', '>', generate_request.processed_registration_id)],
                limit=registrations_batch_size,
                order='id asc'
            )

            registrations_to_process._apply_lead_generation_rules(event_lead_rules=generate_request.event_lead_rule_ids)

            if len(registrations_to_process) < registrations_batch_size:
                # done processing
                fulfilled_requests += generate_request
            else:
                # not complete yet, update last processed registration
                generate_request.processed_registration_id = registrations_to_process[-1].id

            if auto_commit:
                # commit after each completed batch/completed request
                # avoids to re-process everything if an issue with one of the requests
                # important as the lead creation process can typically send emails
                # that should not be duped
                self.env.cr.commit()

        if generate_requests - fulfilled_requests:
            # we still have unfinished requests: run the CRON again
            self.env.ref('event_crm.ir_cron_generate_leads')._trigger()

        if fulfilled_requests:
            fulfilled_requests.unlink()
