# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging
from datetime import datetime, timedelta

from openerp import models, fields, api, exceptions, _

from .job import STATES, DONE, PENDING, OpenERPJobStorage, JOB_REGISTRY
from ..session import ConnectorSession
from ..connector import get_openerp_module, is_module_installed

_logger = logging.getLogger(__name__)


class QueueJob(models.Model):
    """ Job status and result """
    _name = 'queue.job'
    _description = 'Queue Job'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _log_access = False

    _order = 'date_created DESC, date_done DESC'

    _removal_interval = 30  # days

    uuid = fields.Char(string='UUID',
                       readonly=True,
                       select=True,
                       required=True)
    user_id = fields.Many2one(comodel_name='res.users',
                              string='User ID',
                              required=True)
    company_id = fields.Many2one(comodel_name='res.company',
                                 string='Company', select=True)
    name = fields.Char(string='Description', readonly=True)
    func_string = fields.Char(string='Task', readonly=True)
    func = fields.Binary(string='Pickled Function',
                         readonly=True,
                         required=True)
    state = fields.Selection(STATES,
                             string='State',
                             readonly=True,
                             required=True,
                             select=True)
    priority = fields.Integer()
    exc_info = fields.Text(string='Exception Info', readonly=True)
    result = fields.Text(string='Result', readonly=True)
    date_created = fields.Datetime(string='Created Date', readonly=True)
    date_started = fields.Datetime(string='Start Date', readonly=True)
    date_enqueued = fields.Datetime(string='Enqueue Time', readonly=True)
    date_done = fields.Datetime(string='Date Done', readonly=True)
    eta = fields.Datetime(string='Execute only after')
    active = fields.Boolean(default=True)
    model_name = fields.Char(string='Model', readonly=True)
    retry = fields.Integer(string='Current try')
    max_retries = fields.Integer(
        string='Max. retries',
        help="The job will fail if the number of tries reach the "
             "max. retries.\n"
             "Retries are infinite when empty.",
    )
    func_name = fields.Char(readonly=True)
    job_function_id = fields.Many2one(comodel_name='queue.job.function',
                                      compute='_compute_channel',
                                      string='Job Function',
                                      readonly=True,
                                      store=True)
    # for searching without JOIN on channels
    channel = fields.Char(compute='_compute_channel', store=True, select=True)

    @api.one
    @api.depends('func_name', 'job_function_id.channel_id')
    def _compute_channel(self):
        func_model = self.env['queue.job.function']
        function = func_model.search([('name', '=', self.func_name)])
        self.job_function_id = function
        self.channel = self.job_function_id.channel

    @api.multi
    def open_related_action(self):
        """ Open the related action associated to the job """
        self.ensure_one()
        session = ConnectorSession(self.env.cr,
                                   self.env.uid,
                                   context=self.env.context)
        storage = OpenERPJobStorage(session)
        job = storage.load(self.uuid)
        action = job.related_action(session)
        if action is None:
            raise exceptions.Warning(_('No action available for this job'))
        return action

    @api.multi
    def _change_job_state(self, state, result=None):
        """ Change the state of the `Job` object itself so it
        will change the other fields (date, result, ...)
        """
        session = ConnectorSession(self.env.cr,
                                   self.env.uid,
                                   context=self.env.context)
        storage = OpenERPJobStorage(session)
        for job in self:
            job = storage.load(job.uuid)
            if state == DONE:
                job.set_done(result=result)
            elif state == PENDING:
                job.set_pending(result=result)
            else:
                raise ValueError('State not supported: %s' % state)
            storage.store(job)

    @api.multi
    def button_done(self):
        result = _('Manually set to done by %s') % self.env.user.name
        self._change_job_state(DONE, result=result)
        return True

    @api.multi
    def requeue(self):
        self._change_job_state(PENDING)
        return True

    @api.multi
    def write(self, vals):
        res = super(QueueJob, self).write(vals)
        if vals.get('state') == 'failed':
            # subscribe the users now to avoid to subscribe them
            # at every job creation
            self._subscribe_users()
            for job in self:
                msg = job._message_failed_job()
                if msg:
                    job.message_post(body=msg,
                                     subtype='connector.mt_job_failed')
        return res

    @api.multi
    def _subscribe_users(self):
        """ Subscribe all users having the 'Connector Manager' group """
        group = self.env.ref('connector.group_connector_manager')
        if not group:
            return
        companies = self.mapped('company_id')
        domain = [('groups_id', '=', group.id)]
        if companies:
            domain.append(('company_id', 'child_of', companies.ids))
        users = self.env['res.users'].search(domain)
        self.message_subscribe_users(user_ids=users.ids)

    @api.multi
    def _message_failed_job(self):
        """ Return a message which will be posted on the job when it is failed.

        It can be inherited to allow more precise messages based on the
        exception informations.

        If nothing is returned, no message will be posted.
        """
        self.ensure_one()
        return _("Something bad happened during the execution of the job. "
                 "More details in the 'Exception Information' section.")

    @api.model
    def _needaction_domain_get(self):
        """ Returns the domain to filter records that require an action
            :return: domain or False is no action
        """
        return [('state', '=', 'failed')]

    @api.model
    def autovacuum(self):
        """ Delete all jobs (active or not) done since more than
        ``_removal_interval`` days.

        Called from a cron.
        """
        deadline = datetime.now() - timedelta(days=self._removal_interval)
        jobs = self.with_context(active_test=False).search(
            [('date_done', '<=', fields.Datetime.to_string(deadline))],
        )
        jobs.unlink()
        return True


class RequeueJob(models.TransientModel):
    _name = 'queue.requeue.job'
    _description = 'Wizard to requeue a selection of jobs'

    @api.model
    def _default_job_ids(self):
        res = False
        context = self.env.context
        if (context.get('active_model') == 'queue.job' and
                context.get('active_ids')):
            res = context['active_ids']
        return res

    job_ids = fields.Many2many(comodel_name='queue.job',
                               string='Jobs',
                               default=_default_job_ids)

    @api.multi
    def requeue(self):
        jobs = self.job_ids
        jobs.requeue()
        return {'type': 'ir.actions.act_window_close'}


class JobChannel(models.Model):
    _name = 'queue.job.channel'
    _description = 'Job Channels'

    name = fields.Char()
    complete_name = fields.Char(compute='_compute_complete_name',
                                string='Complete Name',
                                store=True,
                                readonly=True)
    parent_id = fields.Many2one(comodel_name='queue.job.channel',
                                string='Parent Channel',
                                ondelete='restrict')
    job_function_ids = fields.One2many(comodel_name='queue.job.function',
                                       inverse_name='channel_id',
                                       string='Job Functions')

    _sql_constraints = [
        ('name_uniq',
         'unique(complete_name)',
         'Channel complete name must be unique'),
    ]

    @api.one
    @api.depends('name', 'parent_id', 'parent_id.name')
    def _compute_complete_name(self):
        if not self.name:
            return  # new record
        channel = self
        parts = [channel.name]
        while channel.parent_id:
            channel = channel.parent_id
            parts.append(channel.name)
        self.complete_name = '.'.join(reversed(parts))

    @api.one
    @api.constrains('parent_id', 'name')
    def parent_required(self):
        if self.name != 'root' and not self.parent_id:
            raise exceptions.ValidationError(_('Parent channel required.'))

    @api.multi
    def write(self, values):
        for channel in self:
            if (not self.env.context.get('install_mode') and
                    channel.name == 'root' and
                    ('name' in values or 'parent_id' in values)):
                raise exceptions.Warning(_('Cannot change the root channel'))
        return super(JobChannel, self).write(values)

    @api.multi
    def unlink(self):
        for channel in self:
            if channel.name == 'root':
                raise exceptions.Warning(_('Cannot remove the root channel'))
        return super(JobChannel, self).unlink()

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, record.complete_name))
        return result


class JobFunction(models.Model):
    _name = 'queue.job.function'
    _description = 'Job Functions'
    _log_access = False

    @api.model
    def _default_channel(self):
        return self.env.ref('connector.channel_root')

    name = fields.Char(select=True)
    channel_id = fields.Many2one(comodel_name='queue.job.channel',
                                 string='Channel',
                                 required=True,
                                 default=_default_channel)
    channel = fields.Char(related='channel_id.complete_name',
                          store=True,
                          readonly=True)

    @api.model
    def _find_or_create_channel(self, channel_path):
        channel_model = self.env['queue.job.channel']
        parts = channel_path.split('.')
        parts.reverse()
        channel_name = parts.pop()
        assert channel_name == 'root', "A channel path starts with 'root'"
        # get the root channel
        channel = channel_model.search([('name', '=', channel_name)])
        while parts:
            channel_name = parts.pop()
            parent_channel = channel
            channel = channel_model.search([
                ('name', '=', channel_name),
                ('parent_id', '=', parent_channel.id)],
                limit=1,
            )
            if not channel:
                channel = channel_model.create({
                    'name': channel_name,
                    'parent_id': parent_channel.id,
                })
        return channel

    @api.model
    def _register_jobs(self):
        for func in JOB_REGISTRY:
            if not is_module_installed(self.env, get_openerp_module(func)):
                continue
            func_name = '%s.%s' % (func.__module__, func.__name__)
            if not self.search_count([('name', '=', func_name)]):
                channel = self._find_or_create_channel(func.default_channel)
                self.create({'name': func_name, 'channel_id': channel.id})

    @api.model
    def _setup_complete(self):
        super(JobFunction, self)._setup_complete()
        self._register_jobs()
