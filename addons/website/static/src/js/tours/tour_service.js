odoo.define('website.TourService', function (require) {
"use strict";

const TourService = require('web_tour.TourService');

TourService.include({
    /**
     * Sets an additional observer on the website client action's iframe, in
     * order to process its mutations during the tours.
     *
     * @override
     */
    init() {
        this._super(...arguments);

        this.iframeContainers.push('o_website_editor');
    }
});
return TourService;
});
