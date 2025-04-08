from odoo import http
from odoo.http import request
from odoo.addons.mail.controllers.avatar_card import AvatarCardController

USER_TO_EMPLOYEE_FIELDS = {
    "work_phone": "work_phone",
    "work_email": "work_email",
    "job_title": "job_title",
    "department_id": "department_id",
    "employee_parent_id": "parent_id",
}


class EmployeeAvatarCardController(AvatarCardController):

    def _get_user_fields(self):
        fields = super()._get_user_fields()
        fields.extend(
            [
                *self._get_user_employee_mapping().keys(),
                "employee_ids",
            ]
        )
        return fields

    def _get_user_employee_mapping(self):
        return USER_TO_EMPLOYEE_FIELDS

    def _get_default_employee_multi_company(self, user_id):
        user_to_employee_fields = self._get_user_employee_mapping()
        employees = request.env["hr.employee"].search_read(
                domain=[("user_id", "=", user_id)],
                fields=list(user_to_employee_fields.values()),
                limit=1,
            )
        return employees[0] if employees else False

    def _employee_to_user_mapping(self, employee_mapping, user_mapping):
        user_to_employee_fields = self._get_user_employee_mapping()
        for field_user, field_employee in user_to_employee_fields.items():
            user_mapping[field_user] = employee_mapping[field_employee]
        user_mapping["employee_ids"] = [employee_mapping["id"]]

    @http.route()
    def mail_avatar_card_get_user_info(self, user_id):
        user = super().mail_avatar_card_get_user_info(user_id)
        if user.get("employee_ids"):
            return user
        employee_multi_company = self._get_default_employee_multi_company(user_id)
        if not employee_multi_company:
            return user
        self._employee_to_user_mapping(employee_multi_company, user)
        return user
