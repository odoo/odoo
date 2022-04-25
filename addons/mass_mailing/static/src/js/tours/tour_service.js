odoo.define('mass_mailing.TourService', function (require) {
"use strict";

const TourService = require('web_tour.TourService');

TourService.include({
    /**
     * Sets an additional observer on the snippets editor iframe, in
     * order to process its mutations during the tours.
     *
     * @override
     */
    init() {
        this._super(...arguments);

        this.iframeContainers.push('wysiwyg_iframe');
    }
});
return TourService;
});
