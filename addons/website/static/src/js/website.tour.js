(function () {
    'use strict';

window.openerp.website.EditorBar.include({
    tours: [],
    start: function () {
        var self = this;
        var menu = $('#help-menu');
        _.each(window.openerp.Tour.tours, function (tour) {
            if (tour.mode === "test") {
                return;
            }
            var $menuItem = $($.parseHTML('<li><a href="#">'+tour.name+'</a></li>'));
            $menuItem.click(function () {
                openerp.Tour.run(tour.id);
            });
            menu.append($menuItem);
        });
        return this._super();
    }
});

})();
