/** @odoo-module **/
import { patch } from "@web/core/utils/patch";

import { MOListViewDropdown } from "@mrp/components/wo_list_view_dropdown/wo_list_view_dropdown";

patch(MOListViewDropdown.prototype, {
    async openShopFloor() {
        this.action.doActionButton({
            type: "object",
            resId: this.props.record.resId,
            name: "action_open_mes",
            resModel: "mrp.workorder",
        });
    }
})
