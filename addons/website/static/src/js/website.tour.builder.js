(function () {
    'use strict';

    var website = openerp.website;

    var render = website.tour.render;

    website.EditorBuilderTour = website.EditorTour.extend({
        id: 'builder_tour',
        name: "Website builder",
        init: function (editor) {
            var self = this;
            var $body = $(document.body);
            self.steps = [
                {
                    stepId: 'welcome',
                    orphan: true,
                    backdrop: true,
                    title: "Website builder",
                    content: "We will guide you to build your website content, editing or add a new menu and install an app.",
                    template: render('website.tour_popover', { next: "Start Tutorial", end: "Skip It" }),
                },
            ];
            return this._super();
        },
    });

    website.EditorBar.include({
        start: function () {
            var menu = $('#help-menu');
            var builderTour = new website.EditorBuilderTour(this);
            var $menuItem = $($.parseHTML('<li><a href="#">'+builderTour.name+'</a></li>'));
            $menuItem.click(function () {
                builderTour.reset();
                builderTour.start();
            });
            menu.append($menuItem);
            return this._super();
        },
    });

}());
