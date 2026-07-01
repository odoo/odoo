import { SnoozeTracker } from "@point_of_sale/app/models/utils/snooze_tracker";
import { patch } from "@web/core/utils/patch";

patch(SnoozeTracker.prototype, {
    getActiveSnooze(type, data) {
        if (type == "self-ordering") {
            return this.state.activeSnoozes.find((s) => s.type == "self-ordering");
        }
        return super.getActiveSnooze(type, data);
    },
});
