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
        id: 'event',
        name: "Create an event",
        testPath: /\/event\/[0-9]+\/register/,
        init: function (editor) {
            var self = this;
            self.steps = [
                {
                    title:     "Create an Event",
                    content:   "Let's go through the first steps to publish a new event.",
                    template:  self.popover({ next: "Start Tutorial", end: "Skip It" }),
                },
                {
                    element:   '#content-menu-button',
                    placement: 'left',
                    title:     "Add Content",
                    content:   "The <em>Content</em> menu allows you to create new pages, events, menus, etc.",
                    template:  self.popover({ fixed: true }),
                },
                {
                    element:   'a[data-action=new_event]',
                    placement: 'left',
                    title:     "New Event",
                    content:   "Click here to create a new event.",
                    template:  self.popover({ fixed: true }),
                },
                {
                    element:   '.modal:contains("New Event") input[type=text]',
                    sampleText: 'Advanced Technical Training',
                    placement: 'right',
                    title:     "Create an Event Name",
                    content:   "Create a name for your new event and click <em>'Continue'</em>. e.g: Technical Training",
                },
                {
                    waitNot:   '.modal input[type=text]:not([value!=""])',
                    element:   '.modal button.btn-primary',
                    placement: 'right',
                    title:     "Create Event",
                    content:   "Click <em>Continue</em> to create the event.",
                },
                {
                    waitFor:   '#website-top-navbar button[data-action="save"]:visible',
                    title:     "New Event Created",
                    content:   "This is your new event page. We will edit the event presentation page.",
                    template:  self.popover({ next: "Continue" }),
                },
                {
                    element:   'button[data-action=snippet]',
                    placement: 'bottom',
                    title:     "Layout your event",
                    content:   "Insert blocks to layout the body of your event.",
                    template:  self.popover({ fixed: true }),
                },
                {
                    snippet:   'image-text',
                    placement: 'bottom',
                    title:     "Drag & Drop a block",
                    content:   "Drag the 'Image-Text' block and drop it in your page.",
                    template:  self.popover({ fixed: true }),
                },
                {
                    
                    element:   'button[data-action=snippet]',
                    placement: 'bottom',
                    title:     "Layout your event",
                    content:   "Insert another block to your event.",
                    template:  self.popover({ fixed: true }),
                },
                {
                    snippet:   'text-block',
                    placement: 'bottom',
                    title:     "Drag & Drop a block",
                    content:   "Drag the 'Text Block' in your event page.",
                    template:  self.popover({ fixed: true }),
                },
                {
                    element:   'button[data-action=save]',
                    placement: 'right',
                    title:     "Save your modifications",
                    content:   "Once you click on save, your event is updated.",
                    template:  self.popover({ fixed: true }),
                },
                {
                    waitFor:   'button[data-action=edit]:visible',
                    element:   'button.btn-danger.js_publish_btn',
                    placement: 'top',
                    title:     "Publish your event",
                    content:   "Click to publish your event.",
                },
                {
                    waitFor:   '.js_publish_management button.js_publish_btn.btn-success:visible',
                    element:   '.js_publish_management button[data-toggle="dropdown"]',
                    placement: 'left',
                    title:     "Customize your event",
                    content:   "Click here to customize your event further.",
                },
                {
                    element:   '.js_publish_management ul>li>a:last:visible',
                },
            ];
            return this._super();
        }
    });

}());
