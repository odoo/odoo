# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    l10n_ph_pos_allow_self_line_void = fields.Boolean(
        string="Allow Self Line Void",
        groups="hr.group_hr_user",
        help=(
            "Allow this cashier to delete order lines or reduce quantities in POS "
            "without requiring a separate approver's PIN. The action is still logged "
            "with the cashier as both performer and approver."
        ),
    )

    def _load_pos_data_read(self, records, config):
        read_records = super()._load_pos_data_read(records, config)
        allow_by_id = {
            emp.id: emp.l10n_ph_pos_allow_self_line_void for emp in records.sudo()
        }
        for employee in read_records:
            employee["_l10n_ph_pos_allow_self_line_void"] = allow_by_id.get(
                employee["id"],
                False,
            )
        return read_records
