# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import logging

import requests
from markupsafe import Markup

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError
from odoo.tools import OrderedSet

from odoo.addons.crm.models import crm_stage

_logger = logging.getLogger(__name__)

TYPESAFE_PROVIDERS = {
    'typesafe': {
        'url': 'https://api.typesafe.ai/v1/systemone',
        'model': 'jev-latest',
    },
    'vercel': {
        'url': 'https://ai-gateway.vercel.sh/typesafe/v1/systemone',
        'model': 'typesafe-ai/jev',
    },
    'openrouter': {
        'url': 'https://openrouter.ai/api/v1/systemone',
        'model': 'jev-latest',
    },
}
TYPESAFE_TIMEOUT = 15
TYPESAFE_MIN_CONFIDENCE = 0.6
TYPESAFE_READINESS_LEVELS = [
    "No buying intent: spam, a vendor pitch, a job application or an unrelated request",
    "Curious: asking general questions, gathering information, no project or timeline mentioned",
    "Evaluating: describes a concrete need or project, compares options or asks about features and pricing",
    "Ready to buy: asks for a quote, a demo, a contract or a delivery date, or mentions a budget and a timeline",
]


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    typesafe_done = fields.Boolean(
        'Qualification done', copy=False,
        help="Whether the TypeSafe lead qualification has been performed on this lead.")
    typesafe_readiness = fields.Float(
        'Buying Readiness', copy=False, readonly=True, aggregator='avg',
        help="How ready the contact is to make a purchase decision, from 0% (no buying intent) to 100% (ready to buy), as estimated by TypeSafe.")
    typesafe_spam_probability = fields.Float(
        'Spam Probability', copy=False, readonly=True, aggregator='avg',
        help="Probability that this lead is spam or not a genuine sales prospect, as estimated by TypeSafe.")
    show_typesafe_qualify_button = fields.Boolean(compute='_compute_show_typesafe_qualify_button')

    @api.depends('active', 'probability', 'typesafe_done')
    def _compute_show_typesafe_qualify_button(self):
        for lead in self:
            lead.show_typesafe_qualify_button = lead.active and not lead.typesafe_done and lead.probability != 100

    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)
        icp = self.env['ir.config_parameter'].sudo()
        if icp.get_str('crm.typesafe.api_key') and (icp.get_str('crm.typesafe.qualify.setting') or 'auto') == 'auto':
            cron = self.env.ref('crm_typesafe.ir_cron_lead_qualification', raise_if_not_found=False)
            if cron:
                cron._trigger()
        return leads

    @api.model
    def _typesafe_qualify_leads_cron(self, qualify_hours_delay=24, batch_size=50):
        if not self.env['ir.config_parameter'].sudo().get_str('crm.typesafe.api_key'):
            return
        time_delta = self.env.cr.now() - datetime.timedelta(hours=qualify_hours_delay)
        leads = self.search([
            ('typesafe_done', '=', False),
            '|', ('probability', '<', 100), ('probability', '=', False),
            ('create_date', '>', time_delta),
            ('active', '=', True),
        ])
        leads.typesafe_qualify(batch_size=batch_size, raise_on_error=False)

    def typesafe_qualify(self, *, batch_size=50, raise_on_error=True):
        """ Qualify leads with TypeSafe, one request per lead, by batches of
        ``batch_size`` locked leads. When called from the cron, progress is
        committed after each batch.

        :param bool raise_on_error: raise a UserError when a request fails,
          instead of leaving the lead pending for a later run
        """
        from_cron = bool(self.env.context.get('cron_id'))
        if not from_cron and not self.env['ir.config_parameter'].sudo().get_str('crm.typesafe.api_key'):
            raise UserError(_("Please configure a TypeSafe API key in the CRM settings first."))

        if from_cron:
            self.env['ir.cron']._commit_progress(remaining=len(self))
        all_lead_ids = OrderedSet(self.ids)
        while all_lead_ids:
            leads = self.browse(all_lead_ids).try_lock_for_update(limit=batch_size)
            if not leads:
                _logger.error('A batch of leads could not be qualified (locked): %r', self.browse(all_lead_ids))
                self.env.ref('crm_typesafe.ir_cron_lead_qualification')._trigger(self.env.cr.now() + datetime.timedelta(minutes=5))
                if from_cron:
                    self.env['ir.cron']._commit_progress(remaining=0)
                break
            all_lead_ids -= set(leads._ids)

            if from_cron:
                try:
                    leads._typesafe_process_leads(raise_on_error=raise_on_error)
                    time_left = self.env['ir.cron']._commit_progress(len(leads))
                except Exception:  # noqa: BLE001
                    self.env['ir.cron']._rollback_progress()
                    _logger.error('A batch of leads could not be qualified: %r', leads)
                    time_left = self.env['ir.cron']._commit_progress(len(leads))
                if not time_left:
                    break
            else:
                leads._typesafe_process_leads(raise_on_error=raise_on_error)

    def _typesafe_process_leads(self, raise_on_error=True):
        for lead in self:
            if lead.typesafe_done or lead.probability == 100:
                continue
            try:
                answers = lead._typesafe_request(lead._typesafe_get_questions(), lead._typesafe_get_state())
            except requests.exceptions.RequestException as e:
                _logger.info('TypeSafe qualification of lead %s failed: %s', lead.id, e)
                if raise_on_error:
                    raise UserError(_("Lead qualification failed, please try again later: %s", e)) from e
                continue
            lead._typesafe_apply_answers(answers)

    def _typesafe_get_state(self):
        """ Return the lead as a JSON-serializable state for the model. Only
        content a salesperson would read to qualify the lead is sent: no ids,
        no internal fields. """
        self.ensure_one()
        return {
            'lead': {
                'subject': self.name,
                'notes': tools.html2plaintext(self.description or '')[:4000],
                'contact_name': self.contact_name or '',
                'company_name': self.partner_name or '',
                'email': self.email_from or '',
                'phone': self.phone or '',
                'website': self.website or '',
                'job_position': self.function or '',
                'country': self.country_id.name or '',
                'expected_revenue': self.expected_revenue,
                'sales_team': self.team_id.name or '',
                'source': self.source_id.name or '',
                'medium': self.medium_id.name or '',
                'campaign': self.campaign_id.name or '',
            },
        }

    def _typesafe_get_questions(self):
        """ Independent questions asked over the same state, in a single
        request. Answers cannot see each other; code combines them. """
        return {
            'priority': {
                'type': 'choice',
                'instructions': "Which priority should a salesperson give to `lead`, based on the value and the likelihood of closing a deal?",
                'criteria': {
                    '0': "Low: vague or generic request, little information, unlikely to become a deal soon",
                    '1': "Medium: a plausible prospect that is worth a follow-up, but with no urgency or clear budget",
                    '2': "High: a concrete need, a named company or decision maker, or a meaningful expected revenue",
                    '3': "Very high: a hot prospect with an explicit budget, timeline or request for a quote, demo or contract",
                },
            },
            'readiness': {
                'type': 'score',
                'instructions': "How ready is the contact described in `lead` to make a purchase decision?",
                'criteria': TYPESAFE_READINESS_LEVELS,
            },
            'is_spam': {
                'type': 'noul',
                'instructions': "Is `lead` spam, an unsolicited vendor pitch, a job application, or otherwise not a genuine sales prospect for the company receiving it?",
                'criteria': {
                    'true': "Not a sales prospect: unsolicited advertising, SEO or link building offers, recruitment, scams, or gibberish",
                    'false': "A person or company that could plausibly buy something from us",
                },
            },
        }

    @api.model
    def _typesafe_request(self, questions, state):
        """ Evaluate ``state`` against ``questions`` on TypeSafe's System One
        endpoint and return the answers, keyed as the questions.

        :raise requests.exceptions.RequestException: on network or HTTP error
        """
        icp = self.env['ir.config_parameter'].sudo()
        api_key = icp.get_str('crm.typesafe.api_key')
        provider = TYPESAFE_PROVIDERS.get(icp.get_str('crm.typesafe.provider')) or TYPESAFE_PROVIDERS['typesafe']
        model = icp.get_str('crm.typesafe.model') or provider['model']
        response = requests.post(
            provider['url'],
            headers={'Authorization': f'Bearer {api_key}'},
            json={'model': model, 'state': state, 'questions': questions},
            timeout=TYPESAFE_TIMEOUT,
        )
        if not response.ok:
            try:
                body = response.json()
                message = body.get('message') or body.get('error', {}).get('message')
            except (ValueError, AttributeError):
                message = None
            error = requests.exceptions.HTTPError(
                f"{response.status_code} {response.reason}: {message}" if message else f"{response.status_code} {response.reason}",
                response=response,
            )
            raise error
        return response.json()['answers']

    def _typesafe_apply_answers(self, answers):
        self.ensure_one()
        priority = answers['priority']
        readiness = answers['readiness']
        spam_probability = answers['is_spam']['noul']

        values = {
            'typesafe_done': True,
            'typesafe_readiness': 100.0 * readiness['score'] / (len(TYPESAFE_READINESS_LEVELS) - 1),
            'typesafe_spam_probability': spam_probability,
        }
        priority_values = dict(crm_stage.AVAILABLE_PRIORITIES)
        if priority['confidence'] >= TYPESAFE_MIN_CONFIDENCE and priority['choice'] in priority_values:
            values['priority'] = priority['choice']
        self.write(values)

        lines = [
            _("Buying readiness: %s%%", round(values['typesafe_readiness'])),
            _("Spam probability: %s%%", round(100 * spam_probability)),
        ]
        if 'priority' in values:
            lines.append(_("Priority set to %(priority)s (%(confidence)s%% confidence)",
                           priority=priority_values[values['priority']],
                           confidence=round(100 * priority['confidence'])))
        else:
            lines.append(_("Priority left unchanged: the model was not confident enough (%s%%)",
                           round(100 * priority['confidence'])))
        self.message_post(
            body=Markup('<p>%s</p><ul>%s</ul>') % (
                _("Lead qualified by TypeSafe"),
                Markup('').join(Markup('<li>%s</li>') % line for line in lines),
            ),
            subtype_xmlid='mail.mt_note',
        )
