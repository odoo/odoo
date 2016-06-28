odoo.define('website.tour.banner', function (require) {
'use strict';

var core = require('web.core');
var Tour = require('web.Tour');
var base = require('web_editor.base');

var _t = core._t;

base.ready().done(function () {

    Tour.register({
        id:   'banner',
        name: _t("Build a page"),
        path: '/page/homepage',
        steps: [
            {
                waitNot:   'body.editor_enable',
                title:     _t("Welcome to your website!"),
                content:   _t("This tutorial will guide you to build your home page. We will start by adding a banner."),
                popover:   { next: _t("Start Tutorial"), end: _t("Skip It") },
            },
            {
                waitNot:   '.popover.tour',
                element:   'a[data-action=edit]',
                placement: 'bottom',
                title:     _t("Edit this page"),
                content:   _t("Every page of your website can be modified through the <i>Edit</i> button."),
                popover:   { fixed: true },
            },
            {
                snippet:   '#snippet_structure .oe_snippet:eq(1)',
                placement: 'bottom',
                title:     _t("Drag & Drop a Banner"),
                content:   _t("Drag the Banner block and drop it in your page."),
                popover:   { fixed: true },
            },
            {
                waitFor:   '.oe_overlay_options .oe_options:visible',
                element:   '#wrapwrap .carousel:first div.carousel-content h3',
                placement: 'top',
                title:     _t("Customize banner's text"),
                content:   _t("Click in the text and start editing it."),
                sampleText: 'Here, a customized text',
            },
            {
                waitNot:   '#wrap .carousel:first div.carousel-content:has(h2:'+
                    'containsExact('+_t('Your Banner Title')+')):has(h3:'+
                    'containsExact('+_t('Click to customize this text')+'))',
                element:   '.oe_snippet_parent:visible',
                placement: 'bottom',
                title:     _t("Get banner properties"),
                content:   _t("Select the parent container to get the global options of the banner."),
                popover:   { fixed: true },
            },
            {
                element:   '.oe_overlay_options .oe_options:visible',
                placement: 'bottom',
                title:     _t("Customize the banner"),
                content:   _t("Customize any block through this menu. Try to change the background of the banner."),
                popover:   { next: _t("Continue") },
            },
            {
                waitNot:   '.popover.tour',
                snippet:   '#snippet_structure .oe_snippet:eq(6)',
                placement: 'bottom',
                title:     _t("Drag & Drop This Block"),
                content:   _t("Drag the <em>'Features'</em> block and drop it below the banner."),
                popover:   { fixed: true },
            },
            {
                waitFor:   '.oe_overlay_options .oe_options:visible',
                element:   'button[data-action=save]',
                placement: 'bottom',
                title:     _t("Save your modifications"),
                content:   _t("Publish your page by clicking on the <em>'Save'</em> button."),
                popover:   { fixed: true },
            },
            {
                waitNot:   'body.editor_enable',
                title:     _t("Good Job!"),
                content:   _t("Well done, you created your homepage."),
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
                element:   '.modal-dialog:has(#mobile-viewport) button[data-dismiss=modal]',
                placement: 'right',
                title:     _t("Check Mobile Preview"),
                content:   _t("Scroll to check rendering and then close the mobile preview."),
            },
            {
                waitNot:   '.modal-dialog:has(#mobile-viewport)',
                element:   '#content-menu-button',
                placement: 'right',
                title:     _t("Pages and menus"),
                content:   _t("The 'Content' menu allows you to rename and delete pages or add them to the top menu."),
                popover:   { next: _t("Continue") },
            },
            {
                waitNot:   '.popover.tour',
                element:   '#oe_main_menu_navbar a[data-action=new_page]',
                placement: 'bottom',
                title:     _t("Add new pages"),
                content:   _t("Use this button to add pages"),
                popover:   { next: _t("Close Tutorial") },
            },
        ]
    });
});

});
