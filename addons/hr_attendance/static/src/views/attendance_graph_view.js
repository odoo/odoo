import { registry } from "@web/core/registry";
import { graphView } from "@web/views/graph/graph_view";
import { GraphModel } from "@web/views/graph/graph_model";


export class AttendanceGraphModel extends GraphModel {

    /** @override **/
    async load(searchParams) {
        const activeDomainParam = searchParams.domain.some((index) => Array.isArray(index) && index[0] == "employee_id.active")
        if (!activeDomainParam) {
            searchParams.domain.push(["employee_id.active", "=", true]);
        }
        return super.load(searchParams);
    }
}

const attendanceGraphView = {
    ...graphView,
    Model: AttendanceGraphModel,
};

registry.category("views").add("attendance_graph_view", attendanceGraphView);