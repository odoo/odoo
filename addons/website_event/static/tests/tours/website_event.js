/** @odoo-module **/
    
    import {_t} from "web.core";
    import {Markup} from "web.utils";
    import wTourUtils from "website.tour_utils";
    import "web.legacy_tranlations_loaded";


    wTourUtils.registerWebsitePreviewTour("website_event_tour", {
        test: true,
        url: "/",
    }, [{
        content: _t("Click here to add new content to your website."),
        trigger: ".o_menu_systray .o_new_content_container > a",
        consumeVisibleOnly: true,
        position: 'bottom',
    }, {
        trigger: "a[data-module-xml-id='base.module_website_event']",
        content: _t("Click here to create a new event."),
        position: "bottom",
    }, {
        trigger: '.modal-dialog div[name="name"] input',
        content: Markup(_t("Create a name for your new event and click <em>\"Continue\"</em>. e.g: Technical Training")),
        run: 'text Technical Training',
        position: "left",
    }, {
        trigger: '.modal-dialog div[name=date_begin]',
        content: _t("Open date range picker. Pick a Start date for your event"),
        run: function () {
            $('input[data-field="date_begin"]').val('09/30/2020 08:00:00').change();
            $('input[data-field="date_end"]').val('10/02/2020 23:00:00').change();
            $('input[data-field="date_begin"]').click();
        }
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
        trigger: ".o_website_edit_in_backend > a",
        content: _t("Click here to customize your event further."),
        position: "bottom",
    }]);
