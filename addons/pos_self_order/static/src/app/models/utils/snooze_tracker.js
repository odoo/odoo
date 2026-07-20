import { SnoozeTracker } from "@point_of_sale/app/models/utils/snooze_tracker";
import { patch } from "@web/core/utils/patch";

patch(SnoozeTracker.prototype, {
    getActiveSnooze(type, data) {
        const res = super.getActiveSnooze(...arguments);
        if (!res && type === "self-ordering") {
            for (const snooze of this.state.activeSnoozes) {
                if (snooze.type === type) {
                    return snooze;
                }
            }
        }
        return res;
    },
});
