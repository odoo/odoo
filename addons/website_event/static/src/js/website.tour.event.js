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
                    title: "Create an Event",
                    content: "Let's go through the firsts step to publish a new event.",
                    template: self.popover({ next: "Start Tutorial", end: "Skip It" }),
                },
                {
                    stepId: 'content-menu',
                    element: '#content-menu-button',
                    placement: 'left',
                    reflex: true,
                    title: "Add Content",
                    content: "The <em>Content</em> menu allows to create new pages, events, menus, etc.",
                },
                {
                    stepId: 'new-post-entry',
                    element: 'a[data-action=new_event]',
                    placement: 'left',
                    title: "New Event",
                    content: "Click here to create a new event.",
                    modal: {
                        stopOnClose: true,
                        afterSubmit: 'event-page',
                    },
                },
                {
                    stepId: 'choose-name',
                    element: '.modal input',
                    placement: 'right',
                    title: "Choose an Event Name",
                    content: "Choose a name for your new event and click <em>'Continue'</em>. e.g: Technical Training",
                },
                {
                    stepId: 'event-page',
                    orphan: true,
                    title: "New Event Created",
                    content: "This is your new event page. We will edit the event presentation page.",
                    template: self.popover({ next: "OK" }),
                },
                {
                    stepId: 'event-price',
                    element: '[data-oe-field=price]',
                    placement: 'top',
                    title: "Ticket price",
                    content: "Edit your ticket price.",
                    template: self.popover({ next: "OK" }),
                },
                {
                    stepId: 'add-banner',
                    element: 'button[data-action=snippet]',
                    placement: 'bottom',
                    title: "Layout your event",
                    content: "Insert blocks like 'Banner' to layout the body of your event.",
                    triggers: function () {
                        $('button[data-action=snippet]').one('click', function () {
                            self.moveToNextStep();
                        });
                    },
                },
                {
                    stepId: 'drag-banner',
                    element: '#website-top-navbar [data-snippet-id=carousel].ui-draggable',
                    placement: 'bottom',
                    title: "Drag & Drop a block",
                    content: "Drag the 'Banner' block and drop it in your page.",
                    triggers: function () {
                        self.onSnippetDraggedAdvance('carousel');
                    },
                },
                {
                    stepId: 'add-text-block',
                    element: 'button[data-action=snippet]',
                    placement: 'bottom',
                    title: "Layout your event",
                    content: "Insert another block to your event.",
                    triggers: function () {
                        $('button[data-action=snippet]').one('click', function () {
                            self.moveToNextStep();
                        });
                    },
                },
                {
                    stepId: 'drag-text-block',
                    element: '#website-top-navbar [data-snippet-id=text-block].ui-draggable',
                    placement: 'bottom',
                    title: "Drag & Drop a block",
                    content: "Drag the 'Text Block' block below the banner.",
                    triggers: function () {
                        self.onSnippetDraggedAdvance('text-block');
                    },
                    onHide: function () {
                        window.scrollTo(0, 0);
                    },
                },
                {
                    stepId: 'add-three-columns',
                    element: 'button[data-action=snippet]',
                    placement: 'bottom',
                    title: "Layout your event",
                    content: "Insert a last block to your event.",
                    triggers: function () {
                        $('button[data-action=snippet]').one('click', function () {
                            self.moveToNextStep();
                        });
                    },
                },
                {
                    stepId: 'drag-three-columns',
                    element: '#website-top-navbar [data-snippet-id=three-columns].ui-draggable',
                    placement: 'bottom',
                    title: "Drag & Drop a block",
                    content: "Drag the 'Three Columns' block at the bottom.",
                    triggers: function () {
                        self.onSnippetDraggedAdvance('three-columns');
                    },
                    onHide: function () {
                        window.scrollTo(0, 0);
                    },
                },
                {
                    stepId: 'save-changes',
                    element: 'button[data-action=save]',
                    placement: 'right',
                    reflex: true,
                    title: "Save your modifications",
                    content: "Once you click on save, your event is updated.",
                },
                {
                    stepId: 'publish-event',
                    element: 'button.js_publish_btn',
                    placement: 'top',
                    reflex: true,
                    title: "Publish your event",
                    content: "Click to publish your event.",
                },
                {
                    stepId: 'customize-event',
                    element: '.js_publish_management button:last',
                    placement: 'left',
                    reflex: true,
                    title: "Customize your event",
                    content: "Click here to customize your event further.",
                },
                {
                    stepId: 'edit-event-backend',
                    element: '.js_publish_management ul>li>a',
                    placement: 'left',
                    reflex: true,
                    title: "Customize your event",
                    content: "Click here to edit your event in the backend.",
                },
            ];
            return this._super();
        },
        resume: function () {
            return (this.isCurrentStep('event-page') || this.isCurrentStep('publish-event')) && this._super();
        },
        trigger: function () {
            return (this.resume() && this.testUrl(/^\/event\/[0-9]+\/register/)) || this._super();
        },
    });

}());
