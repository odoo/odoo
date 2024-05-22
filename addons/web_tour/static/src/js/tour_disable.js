odoo.define('web_tour.DisableTour', function (require) {
"use strict";

var local_storage = require('web.local_storage');
var TourManager = require('web_tour.TourManager');
var utils = require('web_tour.utils');

var get_debugging_key = utils.get_debugging_key;

TourManager.include({
    /**
     * Disables tours if Odoo installed with demo data.
     *
     * @override
     */
    _register: function (do_update, tour, name) {
        // Consuming tours which are not run by test case nor currently being debugged
        if (!this.running_tour && !local_storage.getItem(get_debugging_key(name))) {
            this.consumed_tours.push(name);
        }
        return this._super.apply(this, arguments);
    },
});

});
