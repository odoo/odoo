import {
    insertSnippet,
    registerWebsitePreviewTour,
    clickOnEditAndWaitEditMode,
    clickOnSave,
} from "@website/js/tours/tour_utils";
import { editorsWeakMap } from "@html_editor/../tests/tours/helpers/editor";

function websiteCreateEventTourSteps() {
    return [
        {
            content: "Click here to add new content to your website.",
            trigger: ".o_menu_systray .o_new_content_container > button",
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: "[data-module-xml-id='base.module_website_event']",
            content: "Click here to create a new event.",
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: '.modal-dialog .o_field_widget[name="name"] .o_input',
            content: "Create a name for your new event and click Continue. e.g: Technical Training",
            run: "edit Technical Training",
            tooltipPosition: "left",
        },
        {
            trigger: "button[data-field='date_begin']",
            content: "Set the start date",
            run: "click",
        },
        {
            trigger: "input[data-field='date_begin']",
            content: "Set the start date",
            run: "edit 09/30/2020 08:00:00",
        },
        {
            trigger: "button[data-field='date_end']",
            content: "Set the start date",
            run: "click",
        },
        {
            trigger: "input[data-field='date_end']",
            content: "Set the start date",
            run: "edit 10/02/2020 23:00:00",
        },
        {
            trigger:
                ".modal-dialog div[name='event_ticket_ids'] .o_field_x2many_list_row_add a:contains('Add a line')",
            content: "Click here to add a ticket",
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".modal-dialog input[type=text]:not(:value(''))",
        },
        {
            trigger: ".modal-footer button.btn-primary",
            content: "Click Save to create the event.",
            tooltipPosition: "right",
            run: "click",
        },
        ...insertSnippet({
            id: "s_image_text",
            name: "Image - Text",
            groupName: "Content",
        }),
        ...clickOnSave(),
        {
            trigger: ".o_menu_systray_item.o_website_publish_container a",
            content: "Click to publish your event.",
            tooltipPosition: "top",
            run: "click",
        },
        {
            trigger: ".o_website_edit_in_backend > a",
            content: "Click here to customize your event further.",
            tooltipPosition: "bottom",
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
        {
            content: "Wait for events list to load",
            trigger: ":iframe .opt_events_list_columns",
        },
        ...clickOnEditAndWaitEditMode(),
        {
            content: "edit the short description of the event",
            trigger: ":iframe .opt_events_list_columns",
            run: function () {
                const descriptionEl = this.anchor.querySelector("[itemprop='description']");
                descriptionEl.textContent = "new short description";
                const editor = editorsWeakMap.get(this.anchor.ownerDocument);
                editor.shared.history.addStep();
            },
        },
        ...clickOnSave(),
        {
            content: "is short description updated?",
            trigger: ":iframe .opt_events_list_columns small:contains('new short description')",
        },
    ];
}

registerWebsitePreviewTour(
    "website_event_tour",
    {
        url: "/",
    },
    () => [...websiteCreateEventTourSteps(), ...websiteEditEventTourSteps()]
);
