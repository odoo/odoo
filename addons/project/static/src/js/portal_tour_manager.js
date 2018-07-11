odoo.define('project.portal_tour_manager', function (require) {

var TourManager = require('web_tour.TourManager');

TourManager.include({
    /**
     * Disables console logs so as to avoid confusion,
     * given that the tour manager won't perform.
     */
    init: function (parent, consumed_tours) {
        var originalConsoleLog = console.log;
        console.log = function() {};
        this._super.apply(this, arguments);
        console.log = originalConsoleLog;
    },
    /**
     * Disables tours altogether.
     *
     * @override
     */
    _register_all: function (do_update) {},
});
});
