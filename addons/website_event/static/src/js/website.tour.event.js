(function () {
    'use strict';

    var website = openerp.website;

    website.EditorBar.include({
        start: function () {
            this.registerTour(new website.EventTour(this));
            return this._super();
        },
    });

    website.EventTour = website.Tour.extend({
        id: 'event-tutorial',
        name: "Create an event",
        init: function (editor) {
            var self = this;
            self.steps = [
                {
                    stepId: 'welcome-event',
                    orphan: true,
                    backdrop: true,
                    title: "Event",
                    content: "We will show how to create a new event.",
                    template: self.popover({ next: "Start Tutorial", end: "Skip It" }),
                },
                {
                    stepId: 'content-menu',
                    element: '#content-menu-button',
                    placement: 'left',
                    reflex: true,
                    title: "Edit the content",
                    content: "Click here to add content to your site.",
                },
                {
                    stepId: 'new-post-entry',
                    element: 'a[data-action=new_event]',
                    placement: 'left',
                    title: "New event",
                    content: "Click here to create an event.",
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
                },
                {
                    stepId: 'event-page',
                    orphan: true,
                    backdrop: true,
                    title: "New event created",
                    content: "You just created a new event. We are now going to edit it.",
                    template: self.popover({ next: "OK" }),
                },
                {
                    stepId: 'add-block',
                    element: 'button[data-action=snippet]',
                    placement: 'bottom',
                    reflex: true,
                    title: "Layout your event",
                    content: "Insert blocks like text-image to layout the body of your event.",
                },
            ];
            return this._super();
        },
        resume: function () {
            return this.isCurrentStep('event-page') && !this.tour.ended();
        },
        trigger: function () {
            return (this.resume() && this.testUrl(/^\/event\/[0-9]+\/\?enable_editor=1/)) || this._super();
        },
    });

}());
