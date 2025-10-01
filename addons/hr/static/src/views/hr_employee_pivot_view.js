import { pivotView } from "@web/views/pivot/pivot_view";
import { registry } from "@web/core/registry";
import { PivotController } from "@web/views/pivot/pivot_controller";

export class HrEmployeePivotController extends PivotController {
    static template = "hr.EmployeePivotController";
}

const viewRegistry = registry.category("views");

const hrEmployeePivotView = {
    ...pivotView,
    Controller: HrEmployeePivotController,
};

viewRegistry.add("hr_employee_pivot", hrEmployeePivotView);
