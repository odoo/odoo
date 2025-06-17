import { onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { HrActionHelper } from "./hr_action_helper";

/**
 * This patch is used to showActionHelper in hr views
 * (Controller or Renderer depending on where the action helper is defined)
 */
export function patchHrEmployee(Component) {
    patch(Component.components, { HrActionHelper });
    patch(Component.prototype, {
        setup() {
            super.setup();
            this.actionHelperService = useService("hr_action_helper");
            this.showActionHelper = false;
            onWillStart(async () => {
                this.showActionHelper = await this.actionHelperService.showActionHelper(true);
            });
        },
    });
}
