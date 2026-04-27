# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import threading

from ast import literal_eval
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools, _
from odoo.fields import Datetime
from odoo.exceptions import ValidationError, AccessError
from odoo.tools import convert


class MarketingCampaign(models.Model):
    _name = 'marketing.campaign'
    _description = 'Marketing Campaign'
    _inherits = {'utm.campaign': 'utm_campaign_id'}
    _order = 'create_date DESC'

    utm_campaign_id = fields.Many2one('utm.campaign', 'UTM Campaign', ondelete='restrict', required=True)
    active = fields.Boolean(default=True)
    state = fields.Selection([
        ('draft', 'New'),
        ('running', 'Running'),
        ('stopped', 'Stopped')
        ], copy=False, default='draft',
        group_expand=True)
    model_id = fields.Many2one(
        'ir.model', string='Model', index=True, required=True, ondelete='cascade',
        default=lambda self: self.env.ref('base.model_res_partner', raise_if_not_found=False),
        domain="['&', ('is_mail_thread', '=', True), ('model', '!=', 'mail.blacklist')]")
    model_name = fields.Char(string='Model Name', related='model_id.model', readonly=True, store=True)
    unique_field_id = fields.Many2one(
        'ir.model.fields', string='Unique Field',
        compute='_compute_unique_field_id', readonly=False, store=True,
        domain="[('model_id', '=', model_id), ('ttype', 'in', ['char', 'integer', 'many2one', 'text', 'selection'])]",
        help="""Used to avoid duplicates based on model field.\ne.g.
                For model 'Customers', select email field here if you don't
                want to process records which have the same email address""")
    domain = fields.Char(string="Filter", compute='_compute_domain', readonly=False, store=True)
    # Mailing Filter
    mailing_filter_id = fields.Many2one(
        'mailing.filter', string='Favorite Filter',
        domain="[('mailing_model_name', '=', model_name)]",
        compute='_compute_mailing_filter_id', readonly=False, store=True)
    mailing_filter_domain = fields.Char('Favorite filter domain', related='mailing_filter_id.mailing_domain')
    mailing_filter_count = fields.Integer('# Favorite Filters', compute='_compute_mailing_filter_count')
    # activities
    marketing_activity_ids = fields.One2many('marketing.activity', 'campaign_id', string='Activities', copy=False)
    mass_mailing_count = fields.Integer('# Mailings', compute='_compute_mass_mailing_count')
    link_tracker_click_count = fields.Integer('# Clicks', compute='_compute_link_tracker_click_count')
    last_sync_date = fields.Datetime(string='Last activities synchronization', copy=False)
    require_sync = fields.Boolean(string="Sync of participants is required", compute='_compute_require_sync')
    # participants
    participant_ids = fields.One2many('marketing.participant', 'campaign_id', string='Participants', copy=False)
    running_participant_count = fields.Integer(string="# of active participants", compute='_compute_participants')
    completed_participant_count = fields.Integer(string="# of completed participants", compute='_compute_participants')
    total_participant_count = fields.Integer(string="# of active and completed participants", compute='_compute_participants')
    test_participant_count = fields.Integer(string="# of test participants", compute='_compute_participants')

    @api.constrains('model_id', 'mailing_filter_id')
    def _check_mailing_filter_model(self):
        """Check that if the favorite filter is set, it must contain the same target model as campaign"""
        for campaign in self:
            if campaign.mailing_filter_id and campaign.model_id != campaign.mailing_filter_id.mailing_model_id:
                raise ValidationError(
                    _("The saved filter targets different model and is incompatible with this campaign.")
                )

    @api.depends('model_id')
    def _compute_unique_field_id(self):
        for campaign in self:
            campaign.unique_field_id = False

    @api.depends('model_id', 'mailing_filter_id')
    def _compute_domain(self):
        for campaign in self:
            if campaign.mailing_filter_id:
                campaign.domain = campaign.mailing_filter_id.mailing_domain
            else:
                campaign.domain = repr([])

    @api.depends('marketing_activity_ids.require_sync', 'last_sync_date')
    def _compute_require_sync(self):
        for campaign in self:
            if campaign.last_sync_date and campaign.state == 'running':
                activities_changed = campaign.marketing_activity_ids.filtered(lambda activity: activity.require_sync)
                campaign.require_sync = bool(activities_changed)
            else:
                campaign.require_sync = False

    @api.depends('model_id', 'domain')
    def _compute_mailing_filter_count(self):
        filter_data = self.env['mailing.filter']._read_group([
            ('mailing_model_id', 'in', self.model_id.ids)
        ], ['mailing_model_id'], ['__count'])
        mapped_data = {mailing_model.id: count for mailing_model, count in filter_data}
        for campaign in self:
            campaign.mailing_filter_count = mapped_data.get(campaign.model_id.id, 0)

    @api.depends('model_name')
    def _compute_mailing_filter_id(self):
        for mailing in self:
            mailing.mailing_filter_id = False

    @api.depends('marketing_activity_ids.mass_mailing_id')
    def _compute_mass_mailing_count(self):
        # TDE NOTE: this could be optimized but is currently displayed only in a form view, no need to optimize now
        for campaign in self:
            campaign.mass_mailing_count = len(campaign.mapped('marketing_activity_ids.mass_mailing_id').filtered(lambda mailing: mailing.mailing_type == 'mail'))

    @api.depends('utm_campaign_id')
    def _compute_link_tracker_click_count(self):
        click_data = self.env['link.tracker.click'].sudo()._read_group(
            [('campaign_id', 'in', self.utm_campaign_id.ids)],
            ['campaign_id'],
            ['__count']
        )
        mapped_data = {utm_campaign.id: count for utm_campaign, count in click_data}
        for campaign in self:
            campaign.link_tracker_click_count = mapped_data.get(campaign.utm_campaign_id.id, 0)

    @api.depends('participant_ids.state')
    def _compute_participants(self):
        participants_data = self.env['marketing.participant']._read_group(
            [('campaign_id', 'in', self.ids)],
            ['campaign_id', 'state', 'is_test'],
            ['__count'])
        mapped_data = defaultdict(dict)
        for campaign, state, is_test, count in participants_data:
            if is_test:
                mapped_data[campaign.id]['is_test'] = mapped_data[campaign.id].get('is_test', 0) + count
            else:
                mapped_data[campaign.id][state] = count
        for campaign in self:
            campaign_data = mapped_data[campaign.id]
            campaign.running_participant_count = campaign_data.get('running', 0)
            campaign.completed_participant_count = campaign_data.get('completed', 0)
            campaign.total_participant_count = campaign.completed_participant_count + campaign.running_participant_count
            campaign.test_participant_count = campaign_data.get('is_test', 0)

    @api.returns('self')
    def copy(self, default=None):
        """ Copy the activities of the campaign, each parent_id of each child
        activities should be set to the new copied parent activity. """
        new_compaigns = super().copy(dict(default or {}))

        for old_campaign, new_compaign in zip(self, new_compaigns):
            old_to_new = {}

            for marketing_activity_id in old_campaign.marketing_activity_ids:
                new_marketing_activity_id = marketing_activity_id.copy()
                old_to_new[marketing_activity_id] = new_marketing_activity_id
                new_marketing_activity_id.write({
                    'campaign_id': new_compaign.id,
                    'require_sync': False,
                    'trace_ids': False,
                })

            for marketing_activity_id in new_compaign.marketing_activity_ids:
                marketing_activity_id.parent_id = old_to_new.get(
                    marketing_activity_id.parent_id)

        return new_compaigns

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.update({'is_auto_campaign': True})
        return super(MarketingCampaign, self).create(vals_list)

    @api.onchange('model_id')
    def _onchange_model_id(self):
        if any(campaign.marketing_activity_ids for campaign in self):
            return {'warning': {
                'title': _("Warning"),
                'message': _("Switching Target Model invalidates the existing activities. "
                             "Either update your activity actions to match the new Target Model or delete them.")
            }}

    def write(self, vals):
        if not vals.get('active', True):
            vals['state'] = 'stopped'
        return super().write(vals)

    def action_set_synchronized(self):
        """ Reset campaign and activities 'need synchronization' flags. """
        self.write({'last_sync_date': self.env.cr.now()})
        self.mapped('marketing_activity_ids').write({'require_sync': False})

    def action_update_participants(self):
        """ Synchronizes all participants traces based on activities requiring
        synchronization aka it mainly creates and updates 'marketing.trace'
        records. It is done in 2 steps:

         * update traces related to activities requiring sync, based on their
           ``require_sync`` field. For those we update ``schedule date``.
         * create traces for new activities added in the workflow, aka created
           after campaign ``last_sync_date``:
          * 'begin' activities: create traces for all running participants;
          * other activities: create child for traces linked to the parent of
            the newly created activity
          * for 'not' triggers take into account brother traces that are already
            processed e.g. do not schedule 'mail_not_open' if 'mail_open' is
            already processed;

        Note that scheduling is done right after parent processing independently
        of other time considerations.

        This sets both campaign and all activities to be synchronized. It is
        used mainly on campaign form view, when activities have been modified
        by marketing users.
        """
        now = self.env.cr.now()

        for campaign in self:
            # Action 1: On activity modification
            modified_activities = campaign.marketing_activity_ids.filtered(
                lambda activity: activity.require_sync
            )
            traces_to_reschedule = self.env['marketing.trace'].search([
                ('state', '=', 'scheduled'),
                ('activity_id', 'in', modified_activities.ids)])
            traces_to_reschedule._update_schedule_date()

            # Action 2: On activity creation
            created_activities = campaign.marketing_activity_ids.filtered(
                lambda activity: (
                    campaign.last_sync_date and activity.create_date >= campaign.last_sync_date
                )
            )

            # pre-fetch existing traces to avoid duplicates
            existing_traces = self.env['marketing.trace']
            if created_activities:
                existing_traces = self.env['marketing.trace'].search([
                    ('activity_id', 'in', created_activities.ids),
                ])
            for activity in created_activities:
                activity_offset = relativedelta(**{activity.interval_type: activity.interval_number})
                participants_with_traces = existing_traces.filtered(lambda trace: trace.activity_id == activity).participant_id

                # Case 1: Trigger = begin
                # Create new root traces for all running participants -> consider campaign begin date is now to avoid spamming participants
                if activity.trigger_type == 'begin':
                    participants = self.env['marketing.participant'].search([
                        ('state', '=', 'running'),
                        ('campaign_id', '=', campaign.id),
                        ('id', 'not in', participants_with_traces.ids),
                    ])
                    for participant in participants:
                        schedule_date = now + activity_offset
                        self.env['marketing.trace'].create({
                            'activity_id': activity.id,
                            'participant_id': participant.id,
                            'schedule_date': schedule_date,
                        })
                else:
                    valid_parent_traces = self.env['marketing.trace'].search([
                        ('state', '=', 'processed'),
                        ('activity_id', '=', activity.parent_id.id),
                        ('participant_id', 'not in', participants_with_traces.ids),
                    ])

                    # avoid creating new traces that would have processed brother traces already processed
                    # example: do not create a mail_not_click trace if mail_click is already processed
                    if activity.trigger_type in ['mail_not_open', 'mail_not_click', 'mail_not_reply']:
                        opposite_trigger = activity.trigger_type.replace('_not_', '_')
                        brother_traces = self.env['marketing.trace'].search([
                            ('parent_id', 'in', valid_parent_traces.ids),
                            ('trigger_type', '=', opposite_trigger),
                            ('state', '=', 'processed'),
                        ])
                        valid_parent_traces = valid_parent_traces - brother_traces.mapped('parent_id')

                    valid_parent_traces.mapped('participant_id').filtered(lambda participant: participant.state == 'completed').action_set_running()

                    for parent_trace in valid_parent_traces:
                        self.env['marketing.trace'].create({
                            'activity_id': activity.id,
                            'participant_id': parent_trace.participant_id.id,
                            'parent_id': parent_trace.id,
                            'schedule_date': Datetime.from_string(parent_trace.schedule_date) + activity_offset,
                        })

        self.action_set_synchronized()

    def action_start_campaign(self):
        if any(not campaign.marketing_activity_ids for campaign in self):
            raise ValidationError(_('You must set up at least one activity to start this campaign.'))

        # trigger CRON job ASAP so that participants are synced
        cron = self.env.ref('marketing_automation.ir_cron_campaign_sync_participants')
        cron._trigger(at=self.env.cr.now())
        self.write({'state': 'running'})

    def action_stop_campaign(self):
        self.write({'state': 'stopped'})

    def action_view_mailings(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("marketing_automation.mail_mass_mailing_action_marketing_automation")
        action['domain'] = [
            '&',
            ('use_in_marketing_automation', '=', True),
            ('id', 'in', self.mapped('marketing_activity_ids.mass_mailing_id').ids),
            ('mailing_type', '=', 'mail')
        ]
        action['context'] = dict(self.env.context)
        action['context'].update({
            # defaults
            'default_mailing_model_id': self.model_id.id,
            'default_campaign_id': self.utm_campaign_id.id,
            'default_use_in_marketing_automation': True,
            'default_mailing_type': 'mail',
            'default_state': 'done',
            # action
            'create': False,
        })
        return action

    def action_view_tracker_statistics(self):
        action = self.env["ir.actions.actions"]._for_xml_id("marketing_automation.link_tracker_action_marketing_campaign")
        action['domain'] = [('campaign_id', 'in', self.utm_campaign_id.ids)]
        return action

    def sync_participants(self):
        """ Synchronize campaign participants, based on records in DB. New
        participants are created taking into account campaign filter and unique
        field. Note that traces for 'begin' activities are created when
        creating participants.

        If records have been unlinked since last synchornization, matching
        participants are set as removed.

        It also updates ``last_sync_date`` that is used to know if a new
        synchronization is necessary, based on activities 'require_sync'
        flag.

        This method is called by a cron mainly. It can be called manually on
        campaign form view.

        :return: new participants to the campaign
        """
        def _uniquify_list(seq):
            seen = set()
            return [x for x in seq if x not in seen and not seen.add(x)]

        participants = self.env['marketing.participant']
        now = self.env.cr.now()
        # auto-commit except in testing mode
        auto_commit = not getattr(threading.current_thread(), 'testing', False)
        for campaign in self.filtered(lambda c: c.marketing_activity_ids):
            if not campaign.last_sync_date:
                campaign.last_sync_date = now

            user_id = campaign.user_id or self.env.user
            RecordModel = self.env[campaign.model_name].with_context(lang=user_id.lang)

            # Fetch existing participants
            participants_data = participants.search_read([('campaign_id', '=', campaign.id)], ['res_id'])
            existing_rec_ids = _uniquify_list([live_participant['res_id'] for live_participant in participants_data])

            record_domain = literal_eval(campaign.domain or "[]")
            db_rec_ids = _uniquify_list(RecordModel.search(record_domain).ids)
            to_create = [rid for rid in db_rec_ids if rid not in existing_rec_ids]  # keep ordered IDs
            to_remove = set(existing_rec_ids) - set(db_rec_ids)
            unique_field = campaign.unique_field_id.sudo()
            if unique_field.name != 'id':
                without_duplicates = []
                existing_records = RecordModel.with_context(prefetch_fields=False).browse(existing_rec_ids).exists()
                # Split the read in batch of 1000 to avoid the prefetch
                # crawling the cache for the next 1000 records to fetch
                unique_field_vals = {rec[unique_field.name]
                                        for index in range(0, len(existing_records), 1000)
                                        for rec in existing_records[index:index+1000]}

                for rec in RecordModel.with_context(prefetch_fields=False).browse(to_create):
                    field_val = rec[unique_field.name]
                    # we exclude the empty recordset with the first condition
                    if (not unique_field.relation or field_val) and field_val not in unique_field_vals:
                        without_duplicates.append(rec.id)
                        unique_field_vals.add(field_val)
                to_create = without_duplicates

            BATCH_SIZE = 100
            for to_create_batch in tools.split_every(BATCH_SIZE, to_create, piece_maker=list):
                participants += participants.create([{
                    'campaign_id': campaign.id,
                    'res_id': rec_id,
                } for rec_id in to_create_batch])

                if auto_commit:
                    self.env.cr.commit()

            if to_remove:
                participants_to_unlink = participants.search([
                    ('res_id', 'in', list(to_remove)),
                    ('campaign_id', '=', campaign.id),
                    ('state', '!=', 'unlinked'),
                ])
                for index in range(0, len(participants_to_unlink), 1000):
                    participants_to_unlink[index:index+1000].action_set_unlink()
                    # Commit only every 100 operation to avoid committing to often
                    # this mean every 10k record. It should be ok, it takes 1sec second to process 10k
                    if auto_commit and not index % (BATCH_SIZE * 100):
                        self.env.cr.commit()

        return participants

    def execute_activities(self):
        """ Execute activities by fetching all scheduled traces and execute them
        if their deadline is in the past. Called by cron or manually on campaign
        form view. """
        for campaign in self:
            campaign.marketing_activity_ids.execute()

    # --------------------------------------
    # Prepare actions data
    # --------------------------------------

    def _prepare_res_partner_category_tag_hot_data(self):
        return {
            'xml_id': 'marketing_automation.res_partner_category_tag_hot',
            'values': {
                'name': _('Hot')
            }
        }

    def _prepare_mailing_list_contact_list_data(self):
        return {
            'xml_id': 'marketing_automation.mailing_list_contact_list',
            'values': {
                'name': _('Confirmed contacts'),
                'active': True,
                'is_public': True
            }
        }

    def _prepare_ir_actions_server_partner_tag_data(self):
        # Add the "Hot" category on partners who will click on a mail sent to them.
        self._create_records_with_xml_ids({'res.partner.category': [self._prepare_res_partner_category_tag_hot_data()]})
        hot_id = self.env.ref('marketing_automation.res_partner_category_tag_hot', raise_if_not_found=False).id
        return {
            'xml_id': 'marketing_automation.ir_actions_server_partner_tag',
            'values': {
                'name': _('Add Hot Category'),
                'model_id': self.env['ir.model']._get_id('res.partner'),
                'update_field_id': self.env["ir.model.fields"]._get_ids('res.partner')['category_id'],
                'update_path': 'category_id',
                'evaluation_type': 'value',
                'resource_ref': f'res.partner.category,{hot_id}',
                'value': str(hot_id)
            }
        }

    def _prepare_ir_actions_server_partner_todo_data(self):
        # Assign activity to admin called Bounced: check email address.
        return {
            'xml_id': 'marketing_automation.ir_actions_server_partner_todo',
            'values': {
                'name': _('Next activity: Check Email Address'),
                'model_id': self.env['ir.model']._get_id('res.partner'),
                'state': 'next_activity',
                'activity_date_deadline_range': 2,
                'activity_date_deadline_range_type': 'days',
                'activity_summary': _('Check Email Address'),
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'activity_user_type': 'generic',
                'activity_user_field_name': 'user_id',
            }
        }

    def _prepare_ir_actions_server_contact_blacklist_data(self):
        # If mail bounces on some contact, blacklist that contact.
        return {
            'xml_id': 'marketing_automation.ir_actions_server_contact_blacklist',
            'values': {
                'name': _('Blacklist record'),
                'model_id': self.env['ir.model']._get_id('mailing.contact'),
                'state': 'code',
                'code':
"""
for record in records:
    record.env['mail.blacklist']._add(
    record.email,
    message='Added in blacklist from automated action',
    )
"""
            }
        }

    def _prepare_ir_actions_server_contact_add_list_data(self):
        # If partner clicks on sent mail, add that contact to separate list called 'Confirmed contacts'.
        return {
            'xml_id': 'marketing_automation.ir_actions_server_contact_add_list',
            'values': {
                'name': _('Add To Confirmed List'),
                'model_id': self.env['ir.model']._get_id('mailing.contact'),
                'state': 'code',
                'code':
"""
mailing_list = env.ref('marketing_automation.mailing_list_contact_list', raise_if_not_found=False)
if mailing_list:
    records.write({'list_ids': [(4, mailing_list.id)]})
"""
            }
        }

    def _prepare_ir_actions_server_partner_message_data(self):
        return {
            'xml_id': 'marketing_automation.ir_actions_server_partner_message',
            'values': {
                'name': _('Message for sales person'),
                'model_id': self.env['ir.model']._get_id('res.partner'),
                'state': 'code',
                'code':
"""
for record in records:
    record.message_post(body='%s is interested in becoming partner.' % record.name)
"""
            }
        }

    def _create_records_with_xml_ids(self, create_xmls):
        for model_name, values in create_xmls.items():
            for record in values:
                module, name = record['xml_id'].split('.')
                if not self.env.ref(f'{module}.{name}', raise_if_not_found=False):
                    created_record = self.env[model_name].sudo().create(record['values'])
                    self.env['ir.model.data'].sudo().create({
                        'name': name,
                        'module': module,
                        'model': model_name,
                        'res_id': created_record.id,
                    })

    # --------------------------------------
    # Sample Templates Creation
    # --------------------------------------

    @api.model
    def get_action_marketing_campaign_from_template(self, template_str):
        if not self.env.su and not self.env.user.has_group('marketing_automation.group_marketing_automation_user'):
            raise AccessError(_('To use this feature you should be an administrator or belong to the marketing automation group.'))
        campaign_templates_info = self.get_campaign_templates_info()
        template = next(
            (template_value
            for group in campaign_templates_info.values()
            for template_key, template_value in group['templates'].items()
            if template_key == template_str),
            False)

        if not template:
            return False
        load_method = template.get('function')
        if not load_method:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'marketing.campaign',
                'views': [[False, 'form']]
            }

        if not load_method.startswith('_get_marketing_template') or not hasattr(self, load_method):
            return
        loaded_method = getattr(self, load_method)
        campaign = loaded_method()

        return {
            'name': 'marketing_automation_templates_action',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_id': campaign.id,
            'res_model': 'marketing.campaign',
            'views': [[False, 'form']]
        }

    @api.model
    def get_campaign_templates_info(self):
        return {
            'misc': {
                'label': _("Misc"),
                'templates': {
                    'start_from_scratch': {
                        'title': _('Start from scratch'),
                        'description': _('Design your own marketing campaign from the ground up.'),
                        'icon': '/marketing_automation/static/img/paintbrush.svg',
                    },
                    'hot_contacts': {
                        'title': _('Tag Hot Contacts'),
                        'description': _('Send a welcome email to contacts and tag them if they click in it.'),
                        'icon': '/marketing_automation/static/img/tag.svg',
                        'function': '_get_marketing_template_hot_contacts_values',
                    },
                    'commercial_prospection': {
                        'title': _('Commercial prospection'),
                        'description': _('Send a free catalog and follow-up according to reactions.'),
                        'icon': '/marketing_automation/static/img/search.svg',
                        'function': '_get_marketing_template_commercial_prospection_values',
                    },
                },
            },
            'marketing': {
                'label': _("Marketing"),
                'templates': {
                    'welcome': {
                        'title': _('Welcome Flow'),
                        'description': _('Send a welcome email to new subscribers, remove the addresses that bounced.'),
                        'icon': '/marketing_automation/static/img/hand_peace.svg',
                        'function': '_get_marketing_template_welcome_values',
                    },
                    'double_opt_in': {
                        'title': _('Double Opt-in'),
                        'description': _('Send an email to new recipients to confirm their consent.'),
                        'icon': '/marketing_automation/static/img/square-check.svg',
                        'function': '_get_marketing_template_double_opt_in_values',
                    },
                }
            }
        }

    def _get_marketing_template_hot_contacts_values(self):
        convert.convert_file(
            self.sudo().env,
            'marketing_automation',
            'data/templates/mail_template_body_welcome_template.xml',
            idref={}, mode='init', kind='data'
        )
        rendered_template = self.env['ir.qweb']._render(self.env.ref('marketing_automation.mail_template_body_welcome_template').id,
                        {'db_host': self.get_base_url(), 'company_website': self.env.company.website})
        prerequisites = {
            'mailing.mailing': [{
                'subject': _('Welcome!'),
                'body_arch': rendered_template,
                'body_html': rendered_template,
                'mailing_model_id': self.env['ir.model']._get_id('res.partner'),
                'reply_to_mode': 'update',
                'use_in_marketing_automation': True,
                'mailing_type': 'mail',
            }],
        }
        for model_name, values in prerequisites.items():
            records = self.env[model_name].create(values)
            for idx, record in enumerate(records):
                prerequisites[model_name][idx] = record

        self._create_records_with_xml_ids({
            'ir.actions.server': [self._prepare_ir_actions_server_partner_tag_data(),
                                  self._prepare_ir_actions_server_partner_todo_data()]
        })

        campaign = self.env['marketing.campaign'].create({
            'name': _('Tag Hot Contacts'),
            'domain': ["&", "&", ("email", "!=", False), ("is_blacklisted", "=", False), ("user_ids", "=", False)],
            'model_id': self.env['ir.model']._get_id('res.partner'),
            'unique_field_id': self.env['ir.model.fields']._get('res.partner', 'email').id
        })
        self.env['marketing.activity'].create([
            {
                'trigger_type': 'begin',
                'activity_type': 'email',
                'interval_type': 'hours',
                'mass_mailing_id': prerequisites['mailing.mailing'][0].id,
                'interval_number': 2,
                'name': _('Send Welcome Email'),
                'campaign_id': campaign.id,
                'child_ids': [
                    (0, 0, {
                        'trigger_type': 'mail_click',
                        'activity_type': 'action',
                        'interval_type': 'hours',
                        'mass_mailing_id': None,
                        'interval_number': 2,
                        'name': _('Add Tag'),
                        'campaign_id': campaign.id,  # use the campaign_id here too,
                        'server_action_id': self.env.ref('marketing_automation.ir_actions_server_partner_tag').id,
                    }),
                    (0, 0, {
                        'trigger_type': 'mail_bounce',
                        'activity_type': 'action',
                        'interval_type': 'hours',
                        'mass_mailing_id': None,
                        'interval_number': 2,
                        'name': _('Check Bounce Contact'),
                        'campaign_id': campaign.id,  # use the campaign_id here too,
                        'server_action_id': self.env.ref('marketing_automation.ir_actions_server_partner_todo').id
                    })
                ]
            }
        ])
        return campaign

    def _get_marketing_template_welcome_values(self):
        convert.convert_file(
            self.sudo().env,
            'marketing_automation',
            'data/templates/mail_template_body_yellow_discount_template.xml',
            idref={}, mode='init', kind='data'
        )
        rendered_template = self.env['ir.qweb']._render(self.env.ref('marketing_automation.mail_template_body_yellow_discount_template').id,
                                                        {'db_host': self.get_base_url(), 'company_website': self.env.company.website})
        prerequisites = {
            'mailing.mailing': [{
                'subject': _('Get 10% OFF'),
                'body_arch': rendered_template,  # set Yellow 10% template
                'body_html': rendered_template,  # set Yellow 10% template
                'mailing_model_id': self.env['ir.model']._get_id('mailing.contact'),
                'reply_to_mode': 'update',
                'mailing_type': 'mail',
                'use_in_marketing_automation': True
            }],
        }
        for model_name, values in prerequisites.items():
            records = self.env[model_name].create(values)
            for idx, record in enumerate(records):
                prerequisites[model_name][idx] = record

        create_xmls = {
            'ir.actions.server': [
                self._prepare_ir_actions_server_contact_blacklist_data()
            ],
        }
        self._create_records_with_xml_ids(create_xmls)

        campaign = self.env['marketing.campaign'].create({
            'name': _('Welcome Flow'),
            'domain': ["&", ("email", "!=", False), ("is_blacklisted", "=", False)],
            'model_id': self.env['ir.model']._get_id('mailing.contact'),
            'unique_field_id': self.env['ir.model.fields']._get('mailing.contact', 'email').id
        })

        self.env['marketing.activity'].create({
            'trigger_type': 'begin',
            'activity_type': 'email',
            'interval_type': 'hours',
            'mass_mailing_id': prerequisites['mailing.mailing'][0].id,
            'interval_number': 2,
            'name': _('Send 10% Welcome Discount'),
            'campaign_id': campaign.id,
            'child_ids': [(0, 0, {
                'trigger_type': 'mail_bounce',
                'activity_type': 'action',
                'interval_type': 'hours',
                'mass_mailing_id': None,
                'interval_number': 2,
                'name': _('Blacklist Bounces'),
                'parent_id': None,
                'campaign_id': campaign.id,  # use the campaign_id here too,
                'server_action_id': self.env.ref('marketing_automation.ir_actions_server_contact_blacklist').id
            })]
        })
        return campaign

    def _get_marketing_template_double_opt_in_values(self):
        convert.convert_file(
            self.sudo().env,
            'marketing_automation',
            'data/templates/mail_template_body_confirmation_template.xml',
            idref={}, mode='init', kind='data'
        )
        rendered_template = self.env['ir.qweb']._render(self.env.ref('marketing_automation.mail_template_body_confirmation_template').id,
                                                {'db_host': self.get_base_url()})
        prerequisites = {
            'mailing.mailing': [{
                'subject': _('Confirmation'),
                'body_arch': rendered_template,
                'body_html': rendered_template,
                'mailing_model_id': self.env['ir.model']._get_id('mailing.contact'),
                'reply_to_mode': 'update',
                'mailing_type': 'mail',
                'use_in_marketing_automation': True
            }],
        }
        for model_name, values in prerequisites.items():
            records = self.env[model_name].create(values)
            for idx, record in enumerate(records):
                prerequisites[model_name][idx] = record

        create_xmls = {
            'mailing.list': [self._prepare_mailing_list_contact_list_data()],
            'ir.actions.server': [
                self._prepare_ir_actions_server_contact_add_list_data()
            ],
        }
        self._create_records_with_xml_ids(create_xmls)

        campaign = self.env['marketing.campaign'].create({
            'name': _('Double Opt-in'),
            'domain': ["&", "&", ("email", "!=", False), ("is_blacklisted", "=", False), ("list_ids", "ilike", "Newsletter")],
            'model_id': self.env['ir.model']._get_id('mailing.contact'),
            'unique_field_id': self.env['ir.model.fields']._get('mailing.contact', 'email').id
        })
        self.env['marketing.activity'].create({
            'trigger_type': 'begin',
            'activity_type': 'email',
            'interval_type': 'hours',
            'mass_mailing_id': prerequisites['mailing.mailing'][0].id,
            'interval_number': 0,
            'name': _('Confirmation'),
            'campaign_id': campaign.id,
            'child_ids': [(0, 0, {
                'trigger_type': 'mail_click',
                'activity_type': 'action',
                'interval_type': 'hours',
                'mass_mailing_id': None,
                'interval_number': 0,
                'name': _('Add to list'),
                'parent_id': None,
                'campaign_id': campaign.id,  # use the campaign_id here too,
                'server_action_id': self.env.ref('marketing_automation.ir_actions_server_contact_add_list').id
            })]
        })
        return campaign

    def _get_marketing_template_commercial_prospection_values(self):
        convert.convert_file(
            self.sudo().env,
            'marketing_automation',
            'data/templates/mail_template_body_join_partnership_template.xml',
            idref={}, mode='init', kind='data'
        )
        convert.convert_file(
            self.sudo().env,
            'marketing_automation',
            'data/templates/mail_template_body_free_trial_template.xml',
            idref={}, mode='init', kind='data'
        )

        free_trial_rendered = self.env['ir.qweb']._render(self.env.ref('marketing_automation.mail_template_body_free_trial_template').id,
                                                          {'company_website': self.env.company.website})
        join_partnership_rendered = self.env['ir.qweb']._render(self.env.ref('marketing_automation.mail_template_body_join_partnership_template').id,
                                                            {'company_website': self.env.company.website})

        prerequisites = {
            'mailing.mailing': [{
                'subject': _('Welcome!'),
                'body_arch': free_trial_rendered,
                'body_html': free_trial_rendered,
                'mailing_model_id': self.env['ir.model']._get_id('res.partner'),
                'reply_to_mode': 'update',
                'mailing_type': 'mail',
                'use_in_marketing_automation': True
            }, {
                'subject': _('Join partnership!'),
                'body_arch': join_partnership_rendered,
                'body_html': join_partnership_rendered,
                'mailing_model_id': self.env['ir.model']._get_id('res.partner'),
                'reply_to_mode': 'update',
                'mailing_type': 'mail',
                'use_in_marketing_automation': True
            }],
        }
        for model_name, values in prerequisites.items():
            records = self.env[model_name].create(values)
            for idx, record in enumerate(records):
                prerequisites[model_name][idx] = record
        create_xmls = {
            'ir.actions.server': [
                self._prepare_ir_actions_server_partner_message_data(),
            ],
        }
        self._create_records_with_xml_ids(create_xmls)

        campaign = self.env['marketing.campaign'].create({
            'name': _('Commercial prospection'),
            'model_id': self.env['ir.model']._get_id('res.partner'),
            'unique_field_id': self.env['ir.model.fields']._get('res.partner', 'email').id
        })
        self.env['marketing.activity'].create([{
            'trigger_type': 'begin',
            'activity_type': 'email',
            'interval_type': 'hours',
            'mass_mailing_id': prerequisites['mailing.mailing'][0].id,
            'interval_number': 1,
            'name': _('Offer free catalog'),
            'campaign_id': campaign.id,
        }, {
            'trigger_type': 'begin',
            'activity_type': 'email',
            'interval_type': 'days',
            'mass_mailing_id': prerequisites['mailing.mailing'][1].id,
            'interval_number': 7,
            'name': _('After 7 days'),
            'campaign_id': campaign.id,
            'child_ids': [(0, 0, {
                'trigger_type': 'mail_reply',
                'activity_type': 'action',
                'interval_type': 'hours',
                'mass_mailing_id': None,
                'interval_number': 1,
                'name': _('Message for sales person'),
                'parent_id': None,
                'campaign_id': campaign.id,  # use the campaign_id here too,
                'server_action_id': self.env.ref('marketing_automation.ir_actions_server_partner_message').id
            })]
        }])
        return campaign
