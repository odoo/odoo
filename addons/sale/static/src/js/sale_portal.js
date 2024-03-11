/** @odoo-module */

import publicWidget from 'web.public.widget';
import "portal.portal"; // force dependencies

publicWidget.registry.PortalHomeCounters.include({
    /**
     * @override
     */
    _getCountersAlwaysDisplayed() {
        return this._super(...arguments).concat(['quotation_count', 'order_count']);
    },
});
