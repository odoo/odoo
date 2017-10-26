odoo.define('web_tour.DisableTour', function (require) {
"use strict";

var TourManager = require('web_tour.TourManager');

TourManager.include({
    /**
     * Disable tours if Odoo installed with demo data.
     *
     * @override
     * @private
     * @param {boolean} do_update
     * @param {Object} tour
     * @param {string} name
     * @returns {Deferred}
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
