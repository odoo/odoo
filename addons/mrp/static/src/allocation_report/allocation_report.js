import { patch } from "@web/core/utils/patch";
import { AllocationReport } from '@stock/allocation_report/allocation_report';

patch(AllocationReport.prototype, {
    _getResModelFromPath(str) {
        if (str === "manufacturing") {
            return "mrp.production";
        }
        return super._getResModelFromPath(...arguments);
    },

    onClickPrint() {
        if (this.doc.res_model === "mrp.production") {
            const options = { additionalContext: { active_ids: [this.doc.id] } };
            return this.actionService.doAction("mrp.action_report_production_order", options);
        }
        return super.onClickPrint();
    },
});
