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
                    triggers: function () {
                        var $doc = $(document);
                        function stopNewEvent () {
                            self.stop();
                        }
                        $doc.on('hide.bs.modal', stopNewEvent);
                        $doc.one('shown.bs.modal', function () {
                            $('.modal button.btn-primary').one('click', function () {
                                $doc.off('hide.bs.modal', stopNewEvent);
                                self.moveToStep('event-page');
                            });
                            self.moveToNextStep();
                        });
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
                    stepId: 'edit-page',
                    element: 'button[data-action=edit]',
                    placement: 'bottom',
                    title: "Edit the event desciption",
                    content: "Edit the page to modify the event description.",
                    triggers: function () {
                        editor.on('tour:editor_bar_loaded', self, self.moveToNextStep);
                    },
                },
                {
                    stepId: 'add-image-text',
                    element: 'button[data-action=snippet]',
                    placement: 'bottom',
                    title: "Layout your event",
                    content: "Insert blocks like text-image to layout the body of your event.",
                    triggers: function () {
                        $('button[data-action=snippet]').one('click', function () {
                            self.moveToNextStep();
                        });
                    },
                },
                {
                    stepId: 'drag-image-text',
                    element: '#website-top-navbar [data-snippet-id=text-block].ui-draggable',
                    placement: 'bottom',
                    title: "Drag & Drop a block",
                    content: "Drag the 'Text Block' block and drop it in your page.",
                    triggers: function () {
                        self.onSnippetDraggedAdvance('text-block');
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
                    stepId: 'publish-post',
                    element: 'button.js_publish_btn',
                    placement: 'right',
                    reflex: true,
                    title: "Publish your event",
                    content: "Click to publish your event.",
                },
            ];
            return this._super();
        },
        resume: function () {
            return (this.isCurrentStep('event-page') || this.isCurrentStep('publish-post')) && this._super();
        },
        trigger: function () {
            return (this.resume() && this.testUrl(/^\/event\/[0-9]+\/register/)) || this._super();
        },
    });

}());
