/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    async _performRPC(route, args) {
        if (route === "/mail/avatar_card/get_user_info") {
            const user_info = await super._performRPC(route, args);
            const { user_id } = args;
            const user = this.pyEnv["res.users"].searchRead([["id", "=", user_id]])[0];
            user_info.job_title = user.job_title;
            user_info.department_id = user.department_id;
            user_info.work_phone = user.work_phone;
            user_info.work_email = user.work_email;
            const employee = this.pyEnv["hr.employee"].searchRead([["user_id", "=", user_id]])[0];
            if (employee) {
                user_info.work_phone = employee.work_phone;
                user_info.work_email = employee.work_email;
                user_info.job_title = employee.job_title;
                user_info.department_id = employee.department_id;
                user_info.employee_parent_id = employee.parent_id;
                user_info.employee_ids = [employee.id];
            }
            return user_info;
        }
        return super._performRPC(route, args);
    }
})
