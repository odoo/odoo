/** @odoo-module */

import publicWidget from 'web.public.widget';
import "@portal/js/portal"; // force dependencies

publicWidget.registry.PortalHomeCounters.include({
    /**
     * @override
     */
    _getCountersAlwaysDisplayed() {
        return this._super(...arguments).concat(['invoice_count']);
    },
});
