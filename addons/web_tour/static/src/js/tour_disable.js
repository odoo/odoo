odoo.define('web_tour.DisableTour', function (require) {
"use strict";

var TourManager = require('web_tour.TourManager');

TourManager.include({
    /**
     * Disables tours if Odoo installed with demo data.
     *
     * @override
     */
    _register: function (do_update, tour, name) {
        // Consuming tours which are not run by test case
        if (!this.running_tour) {
            this.consumed_tours.push(name);
        }
        return this._super.apply(this, arguments);
    },
});

});
