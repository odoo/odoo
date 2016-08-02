odoo.define('web_tour.DebugManager', function (require) {
"use strict";

var DebugManager = require('web.DebugManager');
var Model = require('web.Model');

var tour = require('web_tour.tour');

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
            new Model('web_tour.tour').call('consume', [active_tours]).then(function () {
                window.location.reload();
            });
        }
    },
});

});
