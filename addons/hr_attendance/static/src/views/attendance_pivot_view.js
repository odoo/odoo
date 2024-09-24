import { registry } from "@web/core/registry";
import { pivotView } from "@web/views/pivot/pivot_view";
import { PivotModel } from "@web/views/pivot/pivot_model";


export class AttendancePivotModel extends PivotModel {

    /** @override **/
    async load(searchParams) {
        const activeDomainParam = searchParams.domain.some((index) => Array.isArray(index) && index[0] == "employee_id.active")
        if (!activeDomainParam) {
            searchParams.domain.push(["employee_id.active", "=", true]);
        }
        return super.load(searchParams);
    }
}

const attendancePivotView = {
    ...pivotView,
    Model: AttendancePivotModel,
};

registry.category("views").add("attendance_pivot_view", attendancePivotView);