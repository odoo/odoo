import { patch } from "@web/core/utils/patch";
import { HrActionMenus } from "@hr/search/hr_action_menus/hr_action_menus";

patch(HrActionMenus.prototype, {
    get hasAvailableExports() {
        return false;
    }
});
