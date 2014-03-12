(function () {
    'use strict';

    var website = openerp.website;
    var _t = openerp._t;

    website.EditorBar.include({
        start: function () {
            this.registerTour(new website.Tour.Banner(this));
            return this._super();
        },
    });

    website.Tour.Banner = website.Tour.extend({
        id:   'banner',
        name: "Insert a banner",
        path: '/',
        init: function () {
            var self = this;
            self.steps = [
                {
                    title:     _t("Welcome to your website!"),
                    content:   _t("This tutorial will guide you to build your home page. We will start by adding a banner."),
                    popover:   { next:  _t("Start Tutorial"), end:   _t("Skip It") },
                },
                {
                    waitNot:   '.popover.tour',
                    element:   'button[data-action=edit]',
                    placement: 'bottom',
                    title:     _t("Edit this page"),
                    content:   _t("Every page of your website can be modified through the <i>Edit</i> button."),
                    popover:   { fixed: true },
                },
                {
                    element:   'button[data-action=snippet]',
                    placement: 'bottom',
                    title:     _t("Insert building blocks"),
                    content:   _t("To add content in a page, you can insert building blocks."),
                    popover:   { fixed: true },
                },
                {
                    snippet:   'carousel',
                    placement: 'bottom',
                    title:     _t("Drag & Drop a Banner"),
                    content:   _t("Drag the Banner block and drop it in your page."),
                    popover:   { fixed: true },
                },
                {
                    waitFor:   '.oe_overlay_options .oe_options:visible',
                    element:   '#wrap [data-snippet-id=carousel]:first .carousel-caption > div',
                    placement: 'top',
                    title:     _t("Customize banner's text"),
                    content:   _t("Click in the text and start editing it. Click continue once it's done."),
                    popover:   { next: _t("Continue") },
                },
                {
                    element:   '.oe_overlay_options .oe_options',
                    placement: 'left',
                    title:     _t("Customize the banner"),
                    content:   _t("Customize any block through this menu. Try to change the background of the banner."),
                    popover:   { next: _t("Continue") },
                },
                {
                    waitNot:   '.popover.tour',
                    element:   'button[data-action=snippet]',
                    placement: 'bottom',
                    title:     _t("Add Another Block"),
                    content:   _t("Let's add another building block to your page."),
                    popover:   { fixed: true },
                },
                {
                    element:   'a[href="#snippet_feature"]',
                    placement: 'bottom',
                    title:     _t("Feature blocks list"),
                    content:   _t("Click on 'Features' to see the feature blocks list."),
                    popover:   { fixed: true },
                },
                {
                    snippet:   'features',
                    placement: 'bottom',
                    title:     _t("Drag & Drop This Block"),
                    content:   _t("Drag the <em>'Features'</em> block and drop it below the banner."),
                    popover:   { fixed: true },
                },
                {
                    waitFor:   '.oe_overlay_options .oe_options:visible',
                    element:   'button[data-action=save]',
                    placement: 'right',
                    title:     _t("Save your modifications"),
                    content:   _t("Publish your page by clicking on the <em>'Save'</em> button."),
                    popover:   { fixed: true },
                },
                {
                    waitFor:   'button[data-action=edit]:visible',
                    title:     _t("Congratulation!"),
                    content:   _t("Your homepage has been updated."),
                    popover:   { next: _t("Continue") },
                },
                {
                    waitNot:   '.popover.tour',
                    element:   'a[data-action=show-mobile-preview]',
                    placement: 'bottom',
                    title:     _t("Test Your Mobile Version"),
                    content:   _t("Let's check how your homepage looks like on mobile devices."),
                    popover:   { fixed: true },
                },
                {
                    element:   '.modal:has(#mobile-viewport) button[data-dismiss=modal]',
                    placement: 'right',
                    title:     _t("Check Mobile Preview"),
                    content:   _t("Scroll in the mobile preview to test the rendering. Once it's ok, close this dialog."),
                    popover:   { next: _t("Continue") },
                },
                {
                    waitNot:   '.modal',
                    element:   '#content-menu-button',
                    placement: 'bottom',
                    title:     _t("Add new pages and menus"),
                    content:   _t("The 'Content' menu allows you to add pages or add the top menu."),
                    popover:   { next: _t("Close Tutorial") },
                },
            ];
            return this._super();
        },
    });

}());
