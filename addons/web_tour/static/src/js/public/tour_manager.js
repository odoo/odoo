odoo.define('web_tour.public.TourManager', function (require) {
'use strict';

var TourManager = require('web_tour.TourManager');
var lazyloader = require('web.public.lazyloader');

TourManager.include({
    /**
     * @override
     */
    _waitBeforeTourStart: function () {
        return new Promise(resolve => {
            $(() => {
                lazyloader.allScriptsLoaded.then(() => {
                    setTimeout(resolve);
                });
            })
        });
    },
});
});
