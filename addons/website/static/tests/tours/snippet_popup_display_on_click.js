/** @odoo-module */

import {
    clickOnEditAndWaitEditMode,
    clickOnElement,
    clickOnSave,
    changeOption,
    insertSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';
import { browser } from "@web/core/browser/browser";

registerWebsitePreviewTour("snippet_popup_display_on_click", {
    url: "/",
    edition: true,
}, () => [
    ...insertSnippet({id: "s_text_image", name: "Image - Text", groupName: "Content"}),
    ...insertSnippet({id: "s_popup", name: "Popup", groupName: "Content"}),
    {
        content: "Click inside the popup to access its options menu.",
        trigger: ":iframe .s_popup .s_banner",
        run: "click",
    },
    changeOption("SnippetPopup", 'we-select[data-attribute-name="display"] we-toggler'),
    {
        content: "Click on the display 'On Click' option",
        trigger: "#oe_snippets we-button[data-name='onclick_opt']",
        async run(helpers) {
            // Patch and ignore write on clipboard in tour as we don't have permissions
            const oldWriteText = browser.navigator.clipboard.writeText;
            browser.navigator.clipboard.writeText = () => { console.info('Copy in clipboard ignored!') };
            await helpers.click();
            browser.navigator.clipboard.writeText = oldWriteText;
        }
    },
    {
        content: "Check the copied anchor from the notification toast",
        trigger: ".o_notification_manager .o_notification_content",
        run() {
            const notificationContent = this.anchor.innerText;
            const anchor = notificationContent.substring(notificationContent.indexOf("#"));

            if (anchor !== "#Win-%2420") {
                console.error("The popup anchor is not '#Win-%2420' as expected.");
            }
        },
    },
    clickOnElement("button to close the popup", ":iframe .s_popup_close"),
    clickOnElement("text image snippet button", ":iframe .s_text_image .btn-secondary"),
    {
        content: "Paste the popup anchor in the URL input",
        trigger: "#o_link_dialog_url_input",
        run: "edit #Win-%2420",
    },
    ...clickOnSave(),
    clickOnElement("text image snippet button", ":iframe .s_text_image .btn-secondary"),
    {
        content: "Verify that the popup opens after clicked the button.",
        trigger: ":iframe .s_popup .modal[id='Win-%2420'].show",
        run: "click",
    },
    clickOnElement("button to close the popup", ":iframe .s_popup_close"),
    {
        content: "Go to the 'contactus' page.",
        trigger: ":iframe a[href='/contactus']",
        run: "click",
    },
    {
        content: "wait for the page to be loaded",
        trigger: ".o_website_preview[data-view-xmlid='website.contactus']",
    },
    ...clickOnEditAndWaitEditMode(),
    ...insertSnippet({id: "s_text_image", name: "Image - Text", groupName: "Content"}),
    clickOnElement("text image snippet button", ":iframe .s_text_image .btn-secondary"),
    {
        content: "Add a link to the homepage in the URL input",
        trigger: "#o_link_dialog_url_input",
        run: "edit /",
    },
    {
        content: "Open the page anchor selector",
        trigger: ".o_link_dialog_page_anchor .dropdown-toggle",
        run: "click",
    },
    {
        content: "Click on the popup anchor to add it after the homepage link in the URL input",
        trigger: ".o_link_dialog_page_anchor we-button:contains('#Win-%2420')",
        run: "click",
    },
    ...clickOnSave(),
    clickOnElement("text image snippet button", ":iframe .s_text_image .btn-secondary"),
    {
        trigger: ".o_website_preview[data-view-xmlid='website.homepage']",
    },
    {
        content: "Verify that the popup opens when the homepage page loads.",
        trigger: ":iframe .s_popup .modal[id='Win-%2420'].show",
    },
]);
