/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import {
    insertSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

import { markup } from "@odoo/owl";

registerWebsitePreviewTour("website_event_tour", {
    url: "/",
}, () => [{
    content: _t("Click here to add new content to your website."),
    trigger: ".o_menu_systray .o_new_content_container > a",
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: "a[data-module-xml-id='base.module_website_event']",
    content: _t("Click here to create a new event."),
    tooltipPosition: "bottom",
    run: "click",
}, {
    trigger: '.modal-dialog div[name="name"] input',
    content: markup(_t("Create a name for your new event and click <em>\"Continue\"</em>. e.g: Technical Training")),
    run: "edit Technical Training",
    tooltipPosition: "left",
}, {
    trigger: '.modal-dialog div[name=date_begin]',
    content: _t("Open date range picker. Pick a Start date for your event"),
    run() {
        const el1 = document.querySelector('input[data-field="date_begin"]');
        el1.value = '09/30/2020 08:00:00';
        el1.dispatchEvent(new Event("change", {bubbles: true, cancelable: true}));
        const el2 = document.querySelector('input[data-field="date_end"]');
        el2.value = '10/02/2020 23:00:00';
        el2.dispatchEvent(new Event("change", {bubbles: true, cancelable: true}));
        el1.click();
    }
},
{
    isActive: ["auto"],
    trigger: `.modal-dialog input[type=text]:not(:value(""))`,
},
{
    trigger: '.modal-footer button.btn-primary',
    content: markup(_t("Click <em>Continue</em> to create the event.")),
    tooltipPosition: "right",
    run: "click",
},
...insertSnippet({
    id: "s_image_text",
    name: "Image - Text",
    groupName: "Content",
}), {
    // Wait until the drag and drop is resolved (causing a history step)
    // before clicking save.
    trigger: ".o_we_external_history_buttons button.fa-undo:not([disabled])",
}, {
    trigger: "button[data-action=save]",
    content: _t("Once you click on save, your event is updated."),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ":iframe body:not(.editor_enable)",
},
{
    trigger: ".o_menu_systray_item.o_website_publish_container a",
    content: _t("Click to publish your event."),
    tooltipPosition: "top",
    run: "click",
}, {
    trigger: ".o_website_edit_in_backend > a",
    content: _t("Click here to customize your event further."),
    tooltipPosition: "bottom",
}]);
