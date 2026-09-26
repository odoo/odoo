import { patch } from "@web/core/utils/patch";
import { PortalHomeCounters } from "@portal/interactions/portal_home_counters";

patch(PortalHomeCounters.prototype, {
    getCountersAlwaysDisplayed() {
        return super.getCountersAlwaysDisplayed(...arguments).concat(["pos_order_count"]);
    },
});
