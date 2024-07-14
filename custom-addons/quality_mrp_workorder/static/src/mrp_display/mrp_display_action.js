/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { MrpDisplayAction } from "@mrp_workorder/mrp_display/mrp_display_action";

patch(MrpDisplayAction.prototype, {
    get fieldsStructure() {
        let res = super.fieldsStructure;
        res['mrp.production'].push('quality_check_todo');
        return res;
    }
})