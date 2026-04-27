/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { MrpDisplayAction } from "@mrp_workorder/mrp_display/mrp_display_action";

patch(MrpDisplayAction.prototype, {
    get fieldsStructure() {
        let result = super.fieldsStructure;
        result["quality.check"].push('ip');
        result["quality.check"].push('identifier');
        result["quality.check"].push('boxes');
        return (result);
    }
});
