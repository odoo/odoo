import { registry } from "@web/core/registry";

import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { AttendanceActionHelper } from "@hr_attendance/views/attendance_helper_view";

export class AttendanceListRenderer extends ListRenderer {
    static template = "hr_attendance.AttendanceListRenderer";
    static components = {
        ...AttendanceListRenderer.components,
        AttendanceActionHelper,
    };

    /** @override **/
    get showNoContentHelper() {
        // Rows's length need to be lower than 6 to avoid nocontent overlapping
        return super.showNoContentHelper && this.props.list.count < 6 ;
    }
};

export class AttendanceListModel extends listView.Model {

    /** @override **/
    async load(params = {}) {
        const activeDomainParam = params.domain?.some((index) => Array.isArray(index) && index[0] == "employee_id.active");
        if (!activeDomainParam) {
            params.domain.push(["employee_id.active", "=", true]);
        }
        return super.load(params);
    }
}

export const attendanceListView = {
    ...listView,
    Renderer: AttendanceListRenderer,
    Model: AttendanceListModel,
};

registry.category("views").add("attendance_list_view", attendanceListView);
