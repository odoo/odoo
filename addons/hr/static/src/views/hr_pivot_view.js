import { registry } from "@web/core/registry";
import { pivotView } from "@web/views/pivot/pivot_view";
import { PivotController } from "@web/views/pivot/pivot_controller";
import { HrActionHelper } from "@hr/views/hr_action_helper";

export class HrPivotController extends PivotController {
    static template = "hr.PivotView";
    static components = { ...PivotController.components, HrActionHelper };
}
export const HrPivotView = {
    ...pivotView,
    Controller: HrPivotController,
};

registry.category("views").add("hr_pivot_view", HrPivotView);
