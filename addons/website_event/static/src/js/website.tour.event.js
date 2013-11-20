(function () {
    'use strict';

    var website = openerp.website;

    var render = website.tour.render;

    website.EditorBar.include({
        start: function () {
            this.registerTour(new website.EventTour(this));
            return this._super();
        },
    });

    website.EventTour = website.Tour.extend({
        id: 'event-tutorial',
        name: "Create an event",
        startPath: '/event',
        init: function (editor) {
            var self = this;
            self.steps = [
                {
                    stepId: 'welcome-event',
                    orphan: true,
                    backdrop: true,
                    title: "Event",
                    content: "We will show how to create a new event.",
                    template: render('website.tour_popover', { next: "Start Tutorial", end: "Skip It" }),
                },
                {
                    stepId: 'content-menu',
                    element: '#content-menu-button',
                    placement: 'left',
                    reflex: true,
                    title: "Edit the content",
                    content: "Click here to add content to your site.",
                    template: render('website.tour_popover'),
                },
                {
                    stepId: 'new-post-entry',
                    element: 'a[data-action=new_event]',
                    placement: 'left',
                    title: "New event",
                    content: "Click here to create an event.",
                    template: render('website.tour_popover'),
                    onShow: function () {
                        $(document).one('shown.bs.modal', function () {
                            $('.modal button.btn-primary').click(function () {
                                self.movetoStep('event-page');
                            });
                            self.movetoStep('choose-category');
                        });
                    },
                },
                {
                    stepId: 'choose-name',
                    element: '.modal input',
                    placement: 'right',
                    title: "Choose the event name",
                    content: "Choose a name for the new event and click 'Continue'.",
                    template: render('website.tour_popover'),
                },
                {
                    stepId: 'event-page',
                    orphan: true,
                    backdrop: true,
                    title: "New event created",
                    content: "You just created a new event. We are now going to edit it.",
                    template: render('website.tour_popover', { next: "OK" }),
                },
                {
                    stepId: 'add-block',
                    element: 'button[data-action=snippet]',
                    placement: 'bottom',
                    reflex: true,
                    title: "Layout your event",
                    content: "Insert blocks like text-image to layout the body of your event.",
                    template: render('website.tour_popover'),
                },
            ];
            return this._super();
        },
    });

}());
