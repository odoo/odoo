import { patch } from "@web/core/utils/patch";
import { PortalHomeCounters } from '@portal/interactions/portal_home_counters';

patch(PortalHomeCounters.prototype, {
    /**
     * @override
     */
    getCountersAlwaysDisplayed() {
        return super.getCountersAlwaysDisplayed(...arguments).concat(['order_count']);
    },
});
