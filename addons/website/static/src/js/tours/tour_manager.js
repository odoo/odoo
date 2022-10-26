/** @odoo-module **/

import TourManager from 'web_tour.TourManager';
import core from 'web.core';

TourManager.include({
    /**
     * @override
     */
    async _waitBeforeTourStart() {
        const res = await this._super(...arguments);
        if (window.location.href.indexOf('/web#action=website.website_preview') > 0) {
            // The tour manager waits for the final WebsitePreview client
            // action's url to start the tour, in order to avoid reloading the
            // browser if the it is already at the right location.
            await new Promise(resolve => core.bus.once('WEBSITE-FRONTEND-URL-SET', this, resolve));
        }
        return res;
    },
});
