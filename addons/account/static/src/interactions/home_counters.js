import { HomeCounters } from "@portal/interactions/home_counters";
import { patch } from "@web/core/utils/patch";


patch(HomeCounters.prototype, {
    getCountersAlwaysDisplayed() {
        return super.getCountersAlwaysDisplayed().concat(["invoice_count"]);
    }
});
