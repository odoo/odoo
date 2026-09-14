/** @odoo-module native */
import { registry } from "@web/core/registry";

import { listView, ListRenderer } from "@web/views/list";
import { AttendanceActionHelper } from "@hr_attendance/views/attendance_helper_view";

export class AttendanceListRenderer extends ListRenderer {
    static template = "hr_attendance.AttendanceListRenderer";
    static components = {
        ...ListRenderer.components,
        AttendanceActionHelper,
    };

    get showNoContentHelper() {
        return super.showNoContentHelper && this.props.list.count < 6;
    }
}

export class AttendanceListModel extends listView.Model {
    /**
     * Hide the attendances of archived employees unless the caller asked about
     * them.
     */
    async load(params = {}) {
        // `params.domain` is absent on every reload that means "same domain as
        // before" -- after a save, after a discard -- so pushing into it left
        // those loads unfiltered, and reached the current domain only because
        // it had mutated the search model's own array on the first load and
        // that array was still the one in the config.
        const domain = params.domain ?? this.config.domain ?? [];
        const filtersOnActive = domain.some(
            (condition) =>
                Array.isArray(condition) && condition[0] === "employee_id.active",
        );
        if (filtersOnActive) {
            return super.load(params);
        }
        return super.load({
            ...params,
            domain: [...domain, ["employee_id.active", "=", true]],
        });
    }
}

export const attendanceListView = {
    ...listView,
    Renderer: AttendanceListRenderer,
    Model: AttendanceListModel,
};

registry.category("views").add("attendance_list_view", attendanceListView);
