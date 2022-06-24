odoo.define("website_event.tour", function (require) {
    "use strict";

    const {_t} = require("web.core");
    const {Markup} = require('web.utils');
    const time = require('web.time');
    const wTourUtils = require('website.tour_utils');


    wTourUtils.registerEditionTour("website_event_tour", {
        test: true,
        url: "/",
    }, [{
        content: _t("Click here to add new content to your website."),
        extra_trigger: 'iframe #wrapwrap',
        trigger: ".o_menu_systray .o_new_content_container > a",
        consumeVisibleOnly: true,
        position: 'bottom',
    }, {
        trigger: "a[data-module-xml-id='base.module_website_event']",
        content: _t("Click here to create a new event."),
        position: "bottom",
    }, {
        trigger: '.modal-dialog input[name=name]',
        content: Markup(_t("Create a name for your new event and click <em>\"Continue\"</em>. e.g: Technical Training")),
        run: 'text Technical Training',
        position: "left",
    }, {
        content: _t("Open date range picker."),
        trigger: '.modal-dialog input[name=date_begin]',
    }, {
        trigger: '.modal-dialog input[name=date_begin]',
        extra_trigger: '.daterangepicker',
        content: _t("Pick a Start date for your event"),
        run: function () {
            const daterangepicker = this.$anchor.data('daterangepicker');
            daterangepicker.setStartDate(moment().format(time.getLangDatetimeFormat()));
            daterangepicker.setEndDate(moment().add(1, "d").format(time.getLangDatetimeFormat()));
        }
    }, {
        content: _t("Apply change."),
        trigger: '.daterangepicker:first .applyBtn',
        in_modal: false,
    }, {
        trigger: '.modal-footer button.btn-primary',
        extra_trigger: '.modal-dialog input[type=text][value!=""]',
        content: Markup(_t("Click <em>Continue</em> to create the event.")),
        position: "right",
    }, {
        trigger: "#oe_snippets.o_loaded #snippet_structure .oe_snippet:eq(2) .oe_snippet_thumbnail",
        content: _t("Drag this block and drop it in your page."),
        position: "bottom",
        run: "drag_and_drop",
    }, {
        trigger: "button[data-action=save]",
        content: _t("Once you click on save, your event is updated."),
        position: "bottom",
        extra_trigger: "iframe .o_dirty",
    }, {
        trigger: ".o_menu_systray_item .o_switch_danger_success",
        extra_trigger: "iframe body:not(.editor_enable)",
        content: _t("Click to publish your event."),
        position: "top",
    }, {
        trigger: ".o_menu_systray_item.o_website_edit_in_backend",
        content: _t("Click here to customize your event further."),
        position: "bottom",
    }]);
});
