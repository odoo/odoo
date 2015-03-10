odoo.define('website.tour', ['web.Tour', 'website.editor'], function (require) {
'use strict';

var Tour = require('web.Tour');
var editor = require('website.editor');


editor.EditorBar.include({
    tours: [],
    start: function () {
        var self = this;
        var menu = $('#help-menu');
        _.each(Tour.tours, function (tour) {
            if (tour.mode === "test") {
                return;
            }
            var $menuItem = $($.parseHTML('<li><a href="#">'+tour.name+'</a></li>'));
            $menuItem.click(function () {
                Tour.run(tour.id);
            });
            menu.append($menuItem);
        });
        return this._super();
    }
});

});
