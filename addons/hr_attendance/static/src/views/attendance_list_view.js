/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";

export class AttendanceListModel extends listView.Model {

    /** @override **/
    async load(params = {}) {
        const activeDomainParam = params.domain &&
            params.domain.some((item) => Array.isArray(item) && item[0] === "employee_id.active");
        if (!activeDomainParam) {
            params.domain = params.domain || [];
            params.domain.push(["employee_id.active", "=", true]);
        }
        return super.load(params);
    }
}

export const attendanceListView = {
    ...listView,
    Model: AttendanceListModel,
};

registry.category("views").add("attendance_list_view", attendanceListView);
