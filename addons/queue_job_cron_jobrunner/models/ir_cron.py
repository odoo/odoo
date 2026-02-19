# Copyright 2022 Camptocamp SA (https://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@camptocamp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class IrCron(models.Model):
    _inherit = "ir.cron"

    queue_job_runner = fields.Boolean(
        help="If checked, the cron is considered to be a queue.job runner.",
    )
