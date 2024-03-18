# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

import requests


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    service_tag_ids = fields.Many2many("device.service.tag")
    biometric_user_id = fields.Char("Biometric User ID", required=True)

    def _check_update_device_config(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("odoo-biometric-attendance.update_device")
        )

    def _get_device_base_api_url(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("odoo-biometric-attendance.device_api_base_url")
        )

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if not self._check_update_device_config():
            return res
        for employee in res:
            for stgid in employee.service_tag_ids:
                data = {
                    "stgid": stgid.service_tag_id,
                    "uid": employee.biometric_user_id,
                    "uname": employee.name,
                }
                try:
                    device_api_base_url = self._get_device_base_api_url()
                    requests.post(device_api_base_url + "/add", data, timeout=10)
                except Exception:
                    raise UserError(
                        _("Error creating user to - %s.") % (stgid.service_tag_id)
                    )
        return res

    def unlink(self):
        update_device = self._check_update_device_config()
        if not update_device:
            return super().unlink()
        for stgid in self.service_tag_ids:
            data = {
                "stgid": stgid.service_tag_id,
                "uid": self.biometric_user_id,
            }
            try:
                device_api_base_url = self._get_device_base_api_url()
                requests.post(device_api_base_url + "/delete", data, timeout=10)
            except Exception:
                raise UserError(
                    _("Error removing user from - %s.") % (stgid.service_tag_id)
                )
        return super().unlink()

    def _update_device_for_tags(self, operation, tag_ids):
        for tag_id in tag_ids:
            service_tag = self.env["device.service.tag"].browse(tag_id)
            data = {
                "stgid": service_tag.service_tag_id,
                "uid": self.employee_ref,
            }
            if operation == "add":
                data["uname"] = self.name
            try:
                device_api_base_url = self._get_device_base_api_url()
                requests.post(f"{device_api_base_url}/{operation}", data, timeout=10)
            except Exception as e:
                raise UserError(
                    _(
                        "Error on operation '{operation}' for user to - "
                        "{service_tag_id}: {error}"
                    ).format(
                        operation=operation,
                        service_tag_id=service_tag.service_tag_id,
                        error=e,
                    )
                )

    def write(self, vals):
        if self._check_update_device_config() and "service_tag_ids" in vals:
            current_tags = set(self.service_tag_ids.ids)
            new_tags = set(vals.get("service_tag_ids")[0][2])

            tags_to_add = new_tags - current_tags
            tags_to_remove = current_tags - new_tags

            if tags_to_remove:
                self._update_device_for_tags("delete", tags_to_remove)
            if tags_to_add:
                self._update_device_for_tags("add", tags_to_add)

        return super().write(vals)
