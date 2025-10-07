# Copyright 2013-2020 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

import ast
import logging
import re
from collections import namedtuple

from odoo import _, api, exceptions, fields, models, tools

from ..fields import JobSerialized

_logger = logging.getLogger(__name__)


regex_job_function_name = re.compile(r"^<([0-9a-z_\.]+)>\.([0-9a-zA-Z_]+)$")


class QueueJobFunction(models.Model):
    _name = "queue.job.function"
    _description = "Job Functions"
    _log_access = False

    JobConfig = namedtuple(
        "JobConfig",
        "channel "
        "retry_pattern "
        "related_action_enable "
        "related_action_func_name "
        "related_action_kwargs "
        "job_function_id ",
    )

    def _default_channel(self):
        return self.env.ref("queue_job.channel_root")

    name = fields.Char(
        compute="_compute_name",
        inverse="_inverse_name",
        index=True,
        store=True,
    )

    # model and method should be required, but the required flag doesn't
    # let a chance to _inverse_name to be executed
    model_id = fields.Many2one(
        comodel_name="ir.model", string="Model", ondelete="cascade"
    )
    method = fields.Char()

    channel_id = fields.Many2one(
        comodel_name="queue.job.channel",
        string="Channel",
        required=True,
        default=lambda r: r._default_channel(),
    )
    channel = fields.Char(related="channel_id.complete_name", store=True, readonly=True)
    retry_pattern = JobSerialized(string="Retry Pattern (serialized)", base_type=dict)
    edit_retry_pattern = fields.Text(
        string="Retry Pattern",
        compute="_compute_edit_retry_pattern",
        inverse="_inverse_edit_retry_pattern",
        help="Pattern expressing from the count of retries on retryable errors,"
        " the number of of seconds to postpone the next execution. Setting the "
        "number of seconds to a 2-element tuple or list will randomize the "
        "retry interval between the 2 values.\n"
        "Example: {1: 10, 5: 20, 10: 30, 15: 300}.\n"
        "Example: {1: (1, 10), 5: (11, 20), 10: (21, 30), 15: (100, 300)}.\n"
        "See the module description for details.",
    )
    related_action = JobSerialized(string="Related Action (serialized)", base_type=dict)
    edit_related_action = fields.Text(
        string="Related Action",
        compute="_compute_edit_related_action",
        inverse="_inverse_edit_related_action",
        help="The action when the button *Related Action* is used on a job. "
        "The default action is to open the view of the record related "
        "to the job. Configured as a dictionary with optional keys: "
        "enable, func_name, kwargs.\n"
        "See the module description for details.",
    )

    @api.depends("model_id.model", "method")
    def _compute_name(self):
        for record in self:
            if not (record.model_id and record.method):
                record.name = ""
                continue
            record.name = self.job_function_name(record.model_id.model, record.method)

    def _inverse_name(self):
        groups = regex_job_function_name.match(self.name)
        if not groups:
            raise exceptions.UserError(_("Invalid job function: {}").format(self.name))
        model_name = groups[1]
        method = groups[2]
        model = (
            self.env["ir.model"].sudo().search([("model", "=", model_name)], limit=1)
        )
        if not model:
            raise exceptions.UserError(_("Model {} not found").format(model_name))
        self.model_id = model.id
        self.method = method

    @api.depends("retry_pattern")
    def _compute_edit_retry_pattern(self):
        for record in self:
            retry_pattern = record._parse_retry_pattern()
            record.edit_retry_pattern = str(retry_pattern)

    def _inverse_edit_retry_pattern(self):
        try:
            edited = (self.edit_retry_pattern or "").strip()
            if edited:
                self.retry_pattern = ast.literal_eval(edited)
            else:
                self.retry_pattern = {}
        except (ValueError, TypeError, SyntaxError) as ex:
            raise exceptions.UserError(
                self._retry_pattern_format_error_message()
            ) from ex

    @api.depends("related_action")
    def _compute_edit_related_action(self):
        for record in self:
            record.edit_related_action = str(record.related_action)

    def _inverse_edit_related_action(self):
        try:
            edited = (self.edit_related_action or "").strip()
            if edited:
                self.related_action = ast.literal_eval(edited)
            else:
                self.related_action = {}
        except (ValueError, TypeError, SyntaxError) as ex:
            raise exceptions.UserError(
                self._related_action_format_error_message()
            ) from ex

    @staticmethod
    def job_function_name(model_name, method_name):
        return "<{}>.{}".format(model_name, method_name)

    def job_default_config(self):
        return self.JobConfig(
            channel="root",
            retry_pattern={},
            related_action_enable=True,
            related_action_func_name=None,
            related_action_kwargs={},
            job_function_id=None,
        )

    def _parse_retry_pattern(self):
        try:
            # as json can't have integers as keys and the field is stored
            # as json, convert back to int
            retry_pattern = {
                int(try_count): postpone_seconds
                for try_count, postpone_seconds in self.retry_pattern.items()
            }
        except ValueError:
            _logger.error(
                "Invalid retry pattern for job function %s,"
                " keys could not be parsed as integers, fallback"
                " to the default retry pattern.",
                self.name,
            )
            retry_pattern = {}
        return retry_pattern

    @tools.ormcache("name")
    def job_config(self, name):
        config = self.search([("name", "=", name)], limit=1)
        if not config:
            return self.job_default_config()
        retry_pattern = config._parse_retry_pattern()
        return self.JobConfig(
            channel=config.channel,
            retry_pattern=retry_pattern,
            related_action_enable=config.related_action.get("enable", True),
            related_action_func_name=config.related_action.get("func_name"),
            related_action_kwargs=config.related_action.get("kwargs", {}),
            job_function_id=config.id,
        )

    def _retry_pattern_format_error_message(self):
        return _(
            "Unexpected format of Retry Pattern for {}.\n"
            "Example of valid format:\n"
            "{{1: 300, 5: 600, 10: 1200, 15: 3000}}"
        ).format(self.name)

    @api.constrains("retry_pattern")
    def _check_retry_pattern(self):
        for record in self:
            retry_pattern = record.retry_pattern
            if not retry_pattern:
                continue

            all_values = list(retry_pattern) + list(retry_pattern.values())
            for value in all_values:
                try:
                    int(value)
                except ValueError as ex:
                    raise exceptions.UserError(
                        record._retry_pattern_format_error_message()
                    ) from ex

    def _related_action_format_error_message(self):
        return _(
            "Unexpected format of Related Action for {}.\n"
            "Example of valid format:\n"
            '{{"enable": True, "func_name": "related_action_foo",'
            ' "kwargs" {{"limit": 10}}}}'
        ).format(self.name)

    @api.constrains("related_action")
    def _check_related_action(self):
        valid_keys = ("enable", "func_name", "kwargs")
        for record in self:
            related_action = record.related_action
            if not related_action:
                continue

            if any(key not in valid_keys for key in related_action):
                raise exceptions.UserError(
                    record._related_action_format_error_message()
                )

    @api.model_create_multi
    def create(self, vals_list):
        records = self.browse()
        if self.env.context.get("install_mode"):
            # installing a module that creates a job function: rebinds the record
            # to an existing one (likely we already had the job function created by
            # the @job decorator previously)
            new_vals_list = []
            for vals in vals_list:
                name = vals.get("name")
                if name:
                    existing = self.search([("name", "=", name)], limit=1)
                    if existing:
                        if not existing.get_metadata()[0].get("noupdate"):
                            existing.write(vals)
                        records |= existing
                        continue
                new_vals_list.append(vals)
            vals_list = new_vals_list
        records |= super().create(vals_list)
        self.clear_caches()
        return records

    def write(self, values):
        res = super().write(values)
        self.clear_caches()
        return res

    def unlink(self):
        res = super().unlink()
        self.clear_caches()
        return res
