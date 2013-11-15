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
                    stepId: 'welcome-builder',
                    orphan: true,
                    backdrop: true,
                    title: "Website builder",
                    content: "We will guide you to build your website content, editing or add a new menu and install an app.",
                    template: render('website.tour_popover', { next: "Start Tutorial", end: "Skip It" }),
                },
                {
                    stepId: 'content-menu',
                    element: '#content-menu-button',
                    placement: 'left',
                    reflex: true,
                    title: "Edit the content",
                    content: "Click here to edit the menu.",
                    template: render('website.tour_popover'),
                },
                {
                    stepId: 'add-menu-entry',
                    element: 'a[data-action=edit-structure]',
                    placement: 'left',
                    reflex: true,
                    title: "Add a new menu entry",
                    content: "Click here to create a new menu entry and manage options.",
                    template: render('website.tour_popover'),
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
