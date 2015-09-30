odoo.define('website.tour.cancel', function (require) {
'use strict';

var Tour = require('web.Tour');
Tour.autoRunning = false;

});

odoo.define('website.tour', function (require) {
'use strict';

var Tour = require('web.Tour');
var website = require('website.website');
var base = require('web_editor.base');

website.TopBar.include({
    tours: [],
    start: function () {
        var $menu = this.$('#help-menu');
        setTimeout(function () {
            _.each(Tour.tours, function (tour) {
                if (tour.mode === "test") {
                    return;
                }
                var $menuItem = $($.parseHTML('<li><a href="#">'+tour.name+'</a></li>'));
                $menuItem.click(function () {
                    Tour.run(tour.id);
                });
                $menu.append($menuItem);
            });
        }, 0);
        return this._super();
    }
});

base.ready().then(Tour.running);

});
