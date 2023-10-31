odoo.define("website_event.tour", function (require) {
    "use strict";

    const {_t} = require("web.core");
    const {Markup} = require('web.utils');
    var tour = require("web_tour.tour");
    var time = require('web.time');

    tour.register("website_event_tour", {
        test: true,
        url: "/",
    }, [{
        content: _t("Click here to add new content to your website."),
        trigger: "body:has(#o_new_content_menu_choices.o_hidden) #new-content-menu > a",
        consumeVisibleOnly: true,
        position: 'bottom',
    }, {
        trigger: "a[data-action=new_event]",
        content: _t("Click here to create a new event."),
        position: "bottom",
    }, {
        trigger: '.modal-dialog #editor_new_event input[name=name]',
        content: Markup(_t("Create a name for your new event and click <em>\"Continue\"</em>. e.g: Technical Training")),
        run: 'text Technical Training',
        position: "left",
    }, {
        trigger: '.modal-dialog #editor_new_event input[name=event_start_end]',
        content: _t("Pick a Start date for your event"),
        run: 'text ' + moment().format(time.getLangDatetimeFormat()) + ' - ' + moment().add(1, "d").format(time.getLangDatetimeFormat()),
    }, {
        trigger: '.modal-footer button.btn-primary',
        extra_trigger: '#editor_new_event input[type=text][value!=""]',
        content: Markup(_t("Click <em>Continue</em> to create the event.")),
        position: "right",
    }, {
        trigger: "#snippet_structure .oe_snippet:eq(2) .oe_snippet_thumbnail",
        content: _t("Drag this block and drop it in your page."),
        position: "bottom",
        run: "drag_and_drop",
    }, {
        trigger: "button[data-action=save]",
        content: _t("Once you click on save, your event is updated."),
        position: "bottom",
        extra_trigger: ".o_dirty",
    }, {
        trigger: ".js_publish_management .js_publish_btn",
        extra_trigger: "body:not(.editor_enable)",
        content: _t("Click to publish your event."),
        position: "top",
    }, {
        trigger: ".css_edit_dynamic",
        extra_trigger: ".js_publish_management .js_publish_btn .css_unpublish:visible",
        content: _t("Click here to customize your event further."),
        position: "bottom",
    }]);
});
