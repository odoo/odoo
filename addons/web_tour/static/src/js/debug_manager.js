odoo.define('web_tour.DebugManager.Backend', function (require) {
"use strict";

var core = require("web.core");
var DebugManager = require('web.DebugManager.Backend');
var Dialog = require("web.Dialog");
var local_storage = require('web.local_storage');

var tour = require('web_tour.tour');
var utils = require('web_tour.utils');

var get_debugging_key = utils.get_debugging_key;

function get_active_tours () {
    return _.difference(_.keys(tour.tours), tour.consumed_tours);
}

DebugManager.include({
    start: function () {
        this.consume_tours_enabled = get_active_tours().length > 0;
        return this._super.apply(this, arguments);
    },
    consume_tours: function () {
        var active_tours = get_active_tours();
        if (active_tours.length > 0) { // tours might have been consumed meanwhile
            this._rpc({
                    model: 'web_tour.tour',
                    method: 'consume',
                    args: [active_tours],
                })
                .then(function () {
                    for (const tourName of active_tours) {
                        local_storage.removeItem(get_debugging_key(tourName));
                    }
                    window.location.reload();
                });
        }
    },
    start_tour: async function () {
        const tours = Object.values(tour.tours).sort((t1, t2) => {
            return (t1.sequence - t2.sequence) || (t1.name < t2.name ? -1 : 1);
        });
        const dialog = new Dialog(this, {
            title: 'Tours',
            $content: core.qweb.render('web_tour.ToursDialog', {
                onboardingTours: tours.filter(t => !t.test),
                testingTours: tours.filter(t => t.test),
            }),
        });
        await dialog.open().opened();
        dialog.$('.o_start_tour').on('click', this._onStartTour.bind(this));
        dialog.$('.o_test_tour').on('click', this._onTestTour.bind(this));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Resets the given tour to its initial step, in onboarding mode.
     *
     * @private
     * @param {MouseEvent}
     */
    _onStartTour(ev) {
        ev.preventDefault();
        tour.reset($(ev.target).data('name'));
    },
    /**
     * Starts the given tour in test mode.
     *
     * @private
     * @param {MouseEvent}
     */
    _onTestTour(ev) {
        ev.preventDefault();
        tour.run($(ev.target).data('name'));
    },
});

});
