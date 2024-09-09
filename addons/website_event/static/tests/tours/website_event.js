/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";

function websiteCreateEventTourSteps() {
    return [
        {
            content: "Click here to add new content to your website.",
            trigger: ".o_menu_systray .o_new_content_container > a",
            consumeVisibleOnly: true,
            position: "bottom",
        },
        {
            trigger: "a[data-module-xml-id='base.module_website_event']",
            content: "Click here to create a new event.",
            position: "bottom",
        },
        {
            trigger: '.modal-dialog div[name="name"] input',
            content: "Create a name for your new event and click Continue. e.g: Technical Training",
            run: "text Technical Training",
            position: "left",
        },
        {
            trigger: ".modal-dialog div[name=date_begin]",
            content: "Open date range picker. Pick a Start date for your event",
            run: function () {
                const el1 = document.querySelector('input[data-field="date_begin"]');
                el1.value = "09/30/2020 08:00:00";
                el1.dispatchEvent(new Event("change", { bubbles: true, cancelable: true }));
                const el2 = document.querySelector('input[data-field="date_end"]');
                el2.value = "10/02/2020 23:00:00";
                el2.dispatchEvent(new Event("change", { bubbles: true, cancelable: true }));
                el1.click();
            },
        },
        {
            trigger: ".modal-footer button.btn-primary",
            extra_trigger: `.modal-dialog input[type=text]:not(:value(""))`,
            content: "Click Continue to create the event.",
            position: "right",
        },
        {
            trigger:
                "#oe_snippets.o_loaded #snippet_structure .oe_snippet:eq(2) .oe_snippet_thumbnail",
            content: "Drag this block and drop it in your page.",
            position: "bottom",
            run: "drag_and_drop_native :iframe #wrapwrap > main",
        },
        {
            trigger: "button[data-action=save]",
            content: "Once you click on save, your event is updated.",
            position: "bottom",
            // Wait until the drag and drop is resolved (causing a history step)
            // before clicking save.
            extra_trigger:
                ".o_we_external_history_buttons button[data-action=undo]:not([disabled])",
        },
        {
            trigger: ".o_menu_systray_item.o_website_publish_container a",
            extra_trigger: ":iframe body:not(.editor_enable)",
            content: "Click to publish your event.",
            position: "top",
        },
        {
            trigger: ".o_website_edit_in_backend > a",
            content: "Click here to customize your event further.",
            position: "bottom",
            isCheck: true,
        },
    ];
}

function websiteEditEventTourSteps() {
    return [
        {
            content: "Redirect to Event Page",
            trigger: ":iframe a[title='Back to All Events']",
            run: "click",
        },
        ...wTourUtils.clickOnEditAndWaitEditMode(),
        {
            content: "edit the short description of the event",
            trigger: ":iframe .opt_events_list_columns small",
            run: "text new short description",
        },
        ...wTourUtils.clickOnSave(),
        {
            content: "is short description updated?",
            trigger: ":iframe .opt_events_list_columns small:contains('new short description')",
            isCheck: true,
        },
    ];
}

wTourUtils.registerWebsitePreviewTour(
    "website_event_tour",
    {
        test: true,
        url: "/",
    },
    () => [...websiteCreateEventTourSteps(), ...websiteEditEventTourSteps()]
);
