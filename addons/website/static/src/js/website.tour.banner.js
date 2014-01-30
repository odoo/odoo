(function () {
    'use strict';

    var website = openerp.website;

    website.EditorBar.include({
        start: function () {
            this.registerTour(new website.BannerTour(this));
            return this._super();
        },
    });

    website.BannerTour = website.Tour.extend({
        id:   'banner',
        name: "Insert a banner",
        path: '/page/website.homepage',
        init: function (editor) {
            var self = this;
            self.steps = [
                {
                    title:    "Welcome to your website!",
                    content:  "This tutorial will guide you to build your home page. We will start by adding a banner.",
                    template: self.popover({ next: "Start Tutorial", end: "Skip It" }),
                    backdrop: true,
                },
                {
                    waitNot:   '.popover.tour',
                    element:   'button[data-action=edit]',
                    placement: 'bottom',
                    title:     "Edit this page",
                    content:   "Every page of your website can be modified through the <i>Edit</i> button.",
                    template:   self.popover({ fixed: true }),
                },
                {
                    element:   'button[data-action=snippet]',
                    placement: 'bottom',
                    title:     "Insert building blocks",
                    content:   "To add content in a page, you can insert building blocks.",
                    template:   self.popover({ fixed: true }),
                },
                {
                    snippet:   'carousel',
                    placement: 'bottom',
                    title:     "Drag & Drop a Banner",
                    content:   "Drag the Banner block and drop it in your page.",
                    template:   self.popover({ fixed: true }),
                },
                {
                    waitFor:   '.oe_overlay_options .oe_options:visible',
                    element:   '#wrap [data-snippet-id=carousel]:first .carousel-caption',
                    sampleText: 'My Title',
                    placement: 'top',
                    title:     "Customize banner's text",
                    content:   "Click in the text and start editing it. Click continue once it's done.",
                },
                {
                    waitNot:   '#wrap [data-snippet-id=carousel]:first .carousel-caption:contains("Your Banner Title")',
                    element:   '.oe_overlay_options .oe_options',
                    placement: 'left',
                    title:     "Customize the banner",
                    content:   "Customize any block through this menu. Try to change the background of the banner.",
                    template:  self.popover({ next: "Continue" }),
                },
                {
                    waitNot:   '.popover.tour',
                    element:   'button[data-action=snippet]',
                    placement: 'bottom',
                    title:     "Add Another Block",
                    content:   "Let's add another building block to your page.",
                    template:   self.popover({ fixed: true }),
                },
                {
                    snippet:   'three-columns',
                    placement: 'bottom',
                    title:     "Drag & Drop a Block",
                    content:   "Drag the <em>'3 Columns'</em> block and drop it below the banner.",
                    template:   self.popover({ fixed: true }),
                },
                {
                    waitFor:   '.oe_overlay_options .oe_options:visible',
                    element:   'button[data-action=save]',
                    placement: 'right',
                    title:     "Save your modifications",
                    content:   "Publish your page by clicking on the <em>'Save'</em> button.",
                    template:   self.popover({ fixed: true }),
                },
                {
                    waitFor:   'button[data-action=edit]:visible',
                    title:     "Congratulation!",
                    content:   "Your homepage has been updated.",
                    template:  self.popover({ next: "Continue" }),
                },
                {
                    waitNot:   '.popover.tour',
                    element:   'a[data-action=show-mobile-preview]',
                    placement: 'bottom',
                    title:     "Test Your Mobile Version",
                    content:   "Let's check how your homepage looks like on mobile devices.",
                    template:   self.popover({ fixed: true }),
                },
                {
                    element:   'button[data-dismiss=modal]',
                    placement: 'right',
                    title:     "Close Mobile Preview",
                    content:   "Scroll in the mobile preview to test the rendering. Once it's ok, close this dialog.",
                },
                {
                    waitNot:   '.modal',
                    title:     "Congrats",
                    content:   "Congratulation. This tour is finished.",
                    template:  self.popover({ fixed: true, next: "Close Tutorial" }),
                },
            ];
            return this._super();
        },
    });

}());
