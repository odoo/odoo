# Copyright 2013-2020 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)


from odoo import _, api, exceptions, fields, models


class QueueJobChannel(models.Model):
    _name = "queue.job.channel"
    _description = "Job Channels"

    name = fields.Char()
    complete_name = fields.Char(
        compute="_compute_complete_name", store=True, readonly=True, recursive=True
    )
    parent_id = fields.Many2one(
        comodel_name="queue.job.channel", string="Parent Channel", ondelete="restrict"
    )
    job_function_ids = fields.One2many(
        comodel_name="queue.job.function",
        inverse_name="channel_id",
        string="Job Functions",
    )
    removal_interval = fields.Integer(
        default=lambda self: self.env["queue.job"]._removal_interval, required=True
    )

    _sql_constraints = [
        ("name_uniq", "unique(complete_name)", "Channel complete name must be unique")
    ]

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for record in self:
            if not record.name:
                complete_name = ""  # new record
            elif record.parent_id:
                complete_name = ".".join([record.parent_id.complete_name, record.name])
            else:
                complete_name = record.name
            record.complete_name = complete_name

    @api.constrains("parent_id", "name")
    def parent_required(self):
        for record in self:
            if record.name != "root" and not record.parent_id:
                raise exceptions.ValidationError(_("Parent channel required."))

    @api.model_create_multi
    def create(self, vals_list):
        records = self.browse()
        if self.env.context.get("install_mode"):
            # installing a module that creates a channel: rebinds the channel
            # to an existing one (likely we already had the channel created by
            # the @job decorator previously)
            new_vals_list = []
            for vals in vals_list:
                name = vals.get("name")
                parent_id = vals.get("parent_id")
                if name and parent_id:
                    existing = self.search(
                        [("name", "=", name), ("parent_id", "=", parent_id)]
                    )
                    if existing:
                        if not existing.get_metadata()[0].get("noupdate"):
                            existing.write(vals)
                        records |= existing
                        continue
                new_vals_list.append(vals)
            vals_list = new_vals_list
        records |= super().create(vals_list)
        return records

    def write(self, values):
        for channel in self:
            if (
                not self.env.context.get("install_mode")
                and channel.name == "root"
                and ("name" in values or "parent_id" in values)
            ):
                raise exceptions.UserError(_("Cannot change the root channel"))
        return super().write(values)

    def unlink(self):
        for channel in self:
            if channel.name == "root":
                raise exceptions.UserError(_("Cannot remove the root channel"))
        return super().unlink()

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, record.complete_name))
        return result
