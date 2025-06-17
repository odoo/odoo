import { onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";

import { pivotView } from "@web/views/pivot/pivot_view";
import { PivotController } from "@web/views/pivot/pivot_controller";
import { PivotRenderer } from "@web/views/pivot/pivot_renderer";
import { patchHrEmployee } from "./patch_hr_employee";
import { useService } from "@web/core/utils/hooks";

export class HrPivotController extends PivotController {
    static template = "hr.PivotView";
}
patchHrEmployee(HrPivotController);

export class HrPivotRenderer extends PivotRenderer {
    static template = "hr.PivotRenderer";

    setup() {
        super.setup();
        this.actionHelperService = useService("hr_action_helper");
        onWillStart(async () => {
            this.showActionHelper = await this.actionHelperService.showActionHelper();
        });
    }
}

export const HrPivotView = {
    ...pivotView,
    Controller: HrPivotController,
    Renderer: HrPivotRenderer,
};

registry.category("views").add("hr_pivot_view", HrPivotView);
