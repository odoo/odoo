odoo.define('web_tour.public.TourManager', function (require) {
'use strict';

var TourManager = require('web_tour.TourManager');
var lazyloader = require('web.public.lazyloader');

TourManager.include({
    /**
     * @override
     */
    _waitBeforeTourStart: function () {
        return this._super.apply(this, arguments).then(function () {
            return lazyloader.allScriptsLoaded;
        }).then(function () {
            return new Promise(function (resolve) {
                setTimeout(resolve);
            });
        });
    },
});
});
