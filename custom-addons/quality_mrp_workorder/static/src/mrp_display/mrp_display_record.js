/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { MrpDisplayRecord } from "@mrp_workorder/mrp_display/mrp_display_record";

patch(MrpDisplayRecord.prototype, {
    async validate() {
        const { resModel, resId } = this.props.record;
        if (resModel === "mrp.production") {
            if (this.record.quality_check_todo) {
                const action = await this.model.orm.call(resModel, "check_quality", [resId]);
                return this._doAction(action);
            }
        }
        return super.validate();
    },

    get displayCloseProductionButton() {
        return super.displayCloseProductionButton && !this.props.production.data.quality_check_todo;
    },
});
