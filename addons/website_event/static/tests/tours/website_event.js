/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";

function websiteCreateEventTourSteps() {
    return [
        {
            content: "Click here to add new content to your website.",
            trigger: ".o_menu_systray .o_new_content_container > a",
            consumeVisibleOnly: true,
        },
        {
            content: "Click here to create a new event.",
            trigger: "a[data-module-xml-id='base.module_website_event']",
        },
        {
            content:
                "Create a name for your new event and click `Continue`. e.g: Technical Training",
            trigger: ".modal-dialog div[name='name'] input",
            run: "text Technical Training",
        },
        {
            content: "Open date range picker. Pick a Start date for your event",
            trigger: ".modal-dialog div[name=date_begin]",
            run: () => {
                document.querySelector("input[data-field='date_begin']").value =
                    "09/30/2020 08:00:00";
                document
                    .querySelector("input[data-field='date_begin']")
                    .dispatchEvent(new Event("change"));

                document.querySelector("input[data-field='date_end']").value =
                    "10/02/2020 23:00:00";
                document
                    .querySelector("input[data-field='date_end']")
                    .dispatchEvent(new Event("change"));

                document.querySelector("input[data-field='date_begin']").click();
            },
        },
        {
            content: "Click `Continue` to create the event.",
            trigger: ".modal-footer button.btn-primary",
            extra_trigger: ".modal-dialog input[type=text][value!='']",
        },
        {
            content: "Drag this block and drop it in your page.",
            trigger:
                "#oe_snippets.o_loaded #snippet_structure .oe_snippet:eq(2) .oe_snippet_thumbnail",
            run: "drag_and_drop_native iframe #wrapwrap > main",
        },
        {
            content: "Once you click on save, your event is updated.",
            trigger: "button[data-action=save]",
            // Wait until the drag and drop is resolved (causing a history step)
            // before clicking save.
            extra_trigger:
                ".o_we_external_history_buttons button[data-action=undo]:not([disabled])",
        },
        {
            content: "Click to publish your event.",
            trigger: ".o_menu_systray_item .o_switch_danger_success",
            extra_trigger: "iframe body:not(.editor_enable)",
        },
    ];
}

function websiteEditEventTourSteps() {
    return [
        {
            content: "Redirect to Event Page",
            trigger: "iframe span:contains('Back to events')",
            run: "click",
        },
        ...wTourUtils.clickOnEditAndWaitEditMode(),
        {
            content: "edit the short description of the event",
            trigger: "iframe .o_wevent_events_list small",
            run: "text new short description",
        },
        ...wTourUtils.clickOnSave(),
        {
            content: "is short description updated?",
            trigger: "iframe .o_wevent_events_list small:contains('new short description')",
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
