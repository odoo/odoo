# Copyright 2013-2020 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

import logging
import random
from datetime import datetime, timedelta

from odoo import _, api, exceptions, fields, models
from odoo.osv import expression
from odoo.tools import config, html_escape

from odoo.addons.base_sparse_field.models.fields import Serialized

from ..delay import Graph
from ..exception import JobError
from ..fields import JobSerialized
from ..job import (
    CANCELLED,
    DONE,
    FAILED,
    PENDING,
    STARTED,
    STATES,
    WAIT_DEPENDENCIES,
    Job,
)

_logger = logging.getLogger(__name__)


class QueueJob(models.Model):
    """Model storing the jobs to be executed."""

    _name = "queue.job"
    _description = "Queue Job"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _log_access = False

    _order = "date_created DESC, date_done DESC"

    _removal_interval = 30  # days
    _default_related_action = "related_action_open_record"

    # This must be passed in a context key "_job_edit_sentinel" to write on
    # protected fields. It protects against crafting "queue.job" records from
    # RPC (e.g. on internal methods). When ``with_delay`` is used, the sentinel
    # is set.
    EDIT_SENTINEL = object()
    _protected_fields = (
        "uuid",
        "name",
        "date_created",
        "model_name",
        "method_name",
        "func_string",
        "channel_method_name",
        "job_function_id",
        "records",
        "args",
        "kwargs",
    )

    uuid = fields.Char(string="UUID", readonly=True, index=True, required=True)
    graph_uuid = fields.Char(
        string="Graph UUID",
        readonly=True,
        index=True,
        help="Single shared identifier of a Graph. Empty for a single job.",
    )
    user_id = fields.Many2one(comodel_name="res.users", string="User ID")
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company", index=True
    )
    name = fields.Char(string="Description", readonly=True)

    model_name = fields.Char(string="Model", readonly=True)
    method_name = fields.Char(readonly=True)
    # record_ids field is only for backward compatibility (e.g. used in related
    # actions), can be removed (replaced by "records") in 14.0
    record_ids = JobSerialized(compute="_compute_record_ids", base_type=list)
    records = JobSerialized(
        string="Record(s)",
        readonly=True,
        base_type=models.BaseModel,
    )
    dependencies = Serialized(readonly=True)
    # dependency graph as expected by the field widget
    dependency_graph = Serialized(compute="_compute_dependency_graph")
    graph_jobs_count = fields.Integer(compute="_compute_graph_jobs_count")
    args = JobSerialized(readonly=True, base_type=tuple)
    kwargs = JobSerialized(readonly=True, base_type=dict)
    func_string = fields.Char(string="Task", readonly=True)

    state = fields.Selection(STATES, readonly=True, required=True, index=True)
    priority = fields.Integer()
    exc_name = fields.Char(string="Exception", readonly=True)
    exc_message = fields.Char(string="Exception Message", readonly=True, tracking=True)
    exc_info = fields.Text(string="Exception Info", readonly=True)
    result = fields.Text(readonly=True)

    date_created = fields.Datetime(string="Created Date", readonly=True)
    date_started = fields.Datetime(string="Start Date", readonly=True)
    date_enqueued = fields.Datetime(string="Enqueue Time", readonly=True)
    date_done = fields.Datetime(readonly=True)
    exec_time = fields.Float(
        string="Execution Time (avg)",
        group_operator="avg",
        help="Time required to execute this job in seconds. Average when grouped.",
    )
    date_cancelled = fields.Datetime(readonly=True)

    eta = fields.Datetime(string="Execute only after")
    retry = fields.Integer(string="Current try")
    max_retries = fields.Integer(
        string="Max. retries",
        help="The job will fail if the number of tries reach the "
        "max. retries.\n"
        "Retries are infinite when empty.",
    )
    # FIXME the name of this field is very confusing
    channel_method_name = fields.Char(string="Complete Method Name", readonly=True)
    job_function_id = fields.Many2one(
        comodel_name="queue.job.function",
        string="Job Function",
        readonly=True,
    )

    channel = fields.Char(index=True)

    identity_key = fields.Char(readonly=True)
    worker_pid = fields.Integer(readonly=True)

    def init(self):
        self._cr.execute(
            "SELECT indexname FROM pg_indexes WHERE indexname = %s ",
            ("queue_job_identity_key_state_partial_index",),
        )
        if not self._cr.fetchone():
            self._cr.execute(
                "CREATE INDEX queue_job_identity_key_state_partial_index "
                "ON queue_job (identity_key) WHERE state in ('pending', "
                "'enqueued', 'wait_dependencies') AND identity_key IS NOT NULL;"
            )

    @api.depends("records")
    def _compute_record_ids(self):
        for record in self:
            record.record_ids = record.records.ids

    @api.depends("dependencies")
    def _compute_dependency_graph(self):
        jobs_groups = self.env["queue.job"].read_group(
            [
                (
                    "graph_uuid",
                    "in",
                    [uuid for uuid in self.mapped("graph_uuid") if uuid],
                )
            ],
            ["graph_uuid", "ids:array_agg(id)"],
            ["graph_uuid"],
        )
        ids_per_graph_uuid = {
            group["graph_uuid"]: group["ids"] for group in jobs_groups
        }
        for record in self:
            if not record.graph_uuid:
                record.dependency_graph = {}
                continue

            graph_jobs = self.browse(ids_per_graph_uuid.get(record.graph_uuid) or [])
            if not graph_jobs:
                record.dependency_graph = {}
                continue

            graph_ids = {graph_job.uuid: graph_job.id for graph_job in graph_jobs}
            graph_jobs_by_ids = {graph_job.id: graph_job for graph_job in graph_jobs}

            graph = Graph()
            for graph_job in graph_jobs:
                graph.add_vertex(graph_job.id)
                for parent_uuid in graph_job.dependencies["depends_on"]:
                    parent_id = graph_ids.get(parent_uuid)
                    if not parent_id:
                        continue
                    graph.add_edge(parent_id, graph_job.id)
                for child_uuid in graph_job.dependencies["reverse_depends_on"]:
                    child_id = graph_ids.get(child_uuid)
                    if not child_id:
                        continue
                    graph.add_edge(graph_job.id, child_id)

            record.dependency_graph = {
                # list of ids
                "nodes": [
                    graph_jobs_by_ids[graph_id]._dependency_graph_vis_node()
                    for graph_id in graph.vertices()
                ],
                # list of tuples (from, to)
                "edges": graph.edges(),
            }

    def _dependency_graph_vis_node(self):
        """Return the node as expected by the JobDirectedGraph widget"""
        default = ("#D2E5FF", "#2B7CE9")
        colors = {
            DONE: ("#C2FABC", "#4AD63A"),
            FAILED: ("#FB7E81", "#FA0A10"),
            STARTED: ("#FFFF00", "#FFA500"),
        }
        return {
            "id": self.id,
            "title": "<strong>%s</strong><br/>%s"
            % (
                html_escape(self.display_name),
                html_escape(self.func_string),
            ),
            "color": colors.get(self.state, default)[0],
            "border": colors.get(self.state, default)[1],
            "shadow": True,
        }

    def _compute_graph_jobs_count(self):
        jobs_groups = self.env["queue.job"].read_group(
            [
                (
                    "graph_uuid",
                    "in",
                    [uuid for uuid in self.mapped("graph_uuid") if uuid],
                )
            ],
            ["graph_uuid"],
            ["graph_uuid"],
        )
        count_per_graph_uuid = {
            group["graph_uuid"]: group["graph_uuid_count"] for group in jobs_groups
        }
        for record in self:
            record.graph_jobs_count = count_per_graph_uuid.get(record.graph_uuid) or 0

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get("_job_edit_sentinel") is not self.EDIT_SENTINEL:
            # Prevent to create a queue.job record "raw" from RPC.
            # ``with_delay()`` must be used.
            raise exceptions.AccessError(
                _("Queue jobs must be created by calling 'with_delay()'.")
            )
        return super(
            QueueJob,
            self.with_context(mail_create_nolog=True, mail_create_nosubscribe=True),
        ).create(vals_list)

    def write(self, vals):
        if self.env.context.get("_job_edit_sentinel") is not self.EDIT_SENTINEL:
            write_on_protected_fields = [
                fieldname for fieldname in vals if fieldname in self._protected_fields
            ]
            if write_on_protected_fields:
                raise exceptions.AccessError(
                    _("Not allowed to change field(s): {}").format(
                        write_on_protected_fields
                    )
                )

        different_user_jobs = self.browse()
        if vals.get("user_id"):
            different_user_jobs = self.filtered(
                lambda records: records.env.user.id != vals["user_id"]
            )

        if vals.get("state") == "failed":
            self._message_post_on_failure()

        result = super().write(vals)

        for record in different_user_jobs:
            # the user is stored in the env of the record, but we still want to
            # have a stored user_id field to be able to search/groupby, so
            # synchronize the env of records with user_id
            super(QueueJob, record).write(
                {"records": record.records.with_user(vals["user_id"])}
            )
        return result

    def open_related_action(self):
        """Open the related action associated to the job"""
        self.ensure_one()
        job = Job.load(self.env, self.uuid)
        action = job.related_action()
        if action is None:
            raise exceptions.UserError(_("No action available for this job"))
        return action

    def open_graph_jobs(self):
        """Return action that opens all jobs of the same graph"""
        self.ensure_one()
        jobs = self.env["queue.job"].search([("graph_uuid", "=", self.graph_uuid)])

        action = self.env["ir.actions.act_window"]._for_xml_id(
            "queue_job.action_queue_job"
        )
        action.update(
            {
                "name": _("Jobs for graph %s") % (self.graph_uuid),
                "context": {},
                "domain": [("id", "in", jobs.ids)],
            }
        )
        return action

    def _change_job_state(self, state, result=None):
        """Change the state of the `Job` object

        Changing the state of the Job will automatically change some fields
        (date, result, ...).
        """
        for record in self:
            job_ = Job.load(record.env, record.uuid)
            if state == DONE:
                job_.set_done(result=result)
                job_.store()
                record.env["queue.job"].flush_model()
                job_.enqueue_waiting()
            elif state == PENDING:
                job_.set_pending(result=result)
                job_.store()
            elif state == CANCELLED:
                job_.set_cancelled(result=result)
                job_.store()
            else:
                raise ValueError("State not supported: %s" % state)

    def button_done(self):
        result = _("Manually set to done by %s") % self.env.user.name
        self._change_job_state(DONE, result=result)
        return True

    def button_cancelled(self):
        result = _("Cancelled by %s") % self.env.user.name
        self._change_job_state(CANCELLED, result=result)
        return True

    def requeue(self):
        jobs_to_requeue = self.filtered(lambda job_: job_.state != WAIT_DEPENDENCIES)
        jobs_to_requeue._change_job_state(PENDING)
        return jobs_to_requeue

    def _message_post_on_failure(self):
        # subscribe the users now to avoid to subscribe them
        # at every job creation
        domain = self._subscribe_users_domain()
        base_users = self.env["res.users"].search(domain)
        for record in self:
            users = base_users | record.user_id
            record.message_subscribe(partner_ids=users.mapped("partner_id").ids)
            msg = record._message_failed_job()
            if msg:
                record.message_post(body=msg, subtype_xmlid="queue_job.mt_job_failed")

    def _subscribe_users_domain(self):
        """Subscribe all users having the 'Queue Job Manager' group"""
        group = self.env.ref("queue_job.group_queue_job_manager")
        if not group:
            return None
        companies = self.mapped("company_id")
        domain = [("groups_id", "=", group.id)]
        if companies:
            domain.append(("company_id", "in", companies.ids))
        return domain

    def _message_failed_job(self):
        """Return a message which will be posted on the job when it is failed.

        It can be inherited to allow more precise messages based on the
        exception informations.

        If nothing is returned, no message will be posted.
        """
        self.ensure_one()
        return _(
            "Something bad happened during the execution of job %s. "
            "More details in the 'Exception Information' section.",
            self.uuid,
        )

    def _needaction_domain_get(self):
        """Returns the domain to filter records that require an action

        :return: domain or False is no action
        """
        return [("state", "=", "failed")]

    def autovacuum(self):
        """Delete all jobs done based on the removal interval defined on the
           channel

        Called from a cron.
        """
        for channel in self.env["queue.job.channel"].search([]):
            deadline = datetime.now() - timedelta(days=int(channel.removal_interval))
            while True:
                jobs = self.search(
                    [
                        "|",
                        ("date_done", "<=", deadline),
                        ("date_cancelled", "<=", deadline),
                        ("channel", "=", channel.complete_name),
                    ],
                    limit=1000,
                )
                if jobs:
                    jobs.unlink()
                    if not config["test_enable"]:
                        self.env.cr.commit()  # pylint: disable=E8102
                else:
                    break
        return True

    def requeue_stuck_jobs(self, enqueued_delta=1, started_delta=0):
        """Fix jobs that are in a bad states

        :param in_queue_delta: lookup time in minutes for jobs
                               that are in enqueued state,
                               0 means that it is not checked

        :param started_delta: lookup time in minutes for jobs
                              that are in started state,
                              0 means that it is not checked,
                              -1 will use `--limit-time-real` config value
        """
        if started_delta == -1:
            started_delta = (config["limit_time_real"] // 60) + 1
        return self._get_stuck_jobs_to_requeue(
            enqueued_delta=enqueued_delta, started_delta=started_delta
        ).requeue()

    def _get_stuck_jobs_domain(self, queue_dl, started_dl):
        domain = []
        now = fields.datetime.now()
        if queue_dl:
            queue_dl = now - timedelta(minutes=queue_dl)
            domain.append(
                [
                    "&",
                    ("date_enqueued", "<=", fields.Datetime.to_string(queue_dl)),
                    ("state", "=", "enqueued"),
                ]
            )
        if started_dl:
            started_dl = now - timedelta(minutes=started_dl)
            domain.append(
                [
                    "&",
                    ("date_started", "<=", fields.Datetime.to_string(started_dl)),
                    ("state", "=", "started"),
                ]
            )
        if not domain:
            raise exceptions.ValidationError(
                _("If both parameters are 0, ALL jobs will be requeued!")
            )
        return expression.OR(domain)

    def _get_stuck_jobs_to_requeue(self, enqueued_delta, started_delta):
        job_model = self.env["queue.job"]
        stuck_jobs = job_model.search(
            self._get_stuck_jobs_domain(enqueued_delta, started_delta)
        )
        return stuck_jobs

    def related_action_open_record(self):
        """Open a form view with the record(s) of the job.

        For instance, for a job on a ``product.product``, it will open a
        ``product.product`` form view with the product record(s) concerned by
        the job. If the job concerns more than one record, it opens them in a
        list.

        This is the default related action.

        """
        self.ensure_one()
        records = self.records.exists()
        if not records:
            return None
        action = {
            "name": _("Related Record"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": records._name,
        }
        if len(records) == 1:
            action["res_id"] = records.id
        else:
            action.update(
                {
                    "name": _("Related Records"),
                    "view_mode": "tree,form",
                    "domain": [("id", "in", records.ids)],
                }
            )
        return action

    def _test_job(self, failure_rate=0):
        _logger.info("Running test job.")
        if random.random() <= failure_rate:
            raise JobError("Job failed")
