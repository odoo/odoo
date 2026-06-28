import { registry } from "@web/core/registry";
import {
    clickOnEditAndWaitEditMode,
    clickOnElement,
    clickOnSave,
    insertSnippet,
    openLinkPopup,
    unfoldOptionsGroup,
    waitForEditMode,
} from "@website/js/tours/tour_utils";
import { browser } from "@web/core/browser/browser";

const oldWriteText = browser.navigator.clipboard.writeText;

registry.category("web_tour.tours").add("snippet_popup_display_on_click", {
    steps: () => [
        waitForEditMode,
        ...insertSnippet({ id: "s_text_image", name: "Image - Text", groupName: "Content" }),
        ...insertSnippet({ id: "s_popup", name: "Popup", groupName: "Content" }),
        {
            content: "Click inside the popup to access its options menu.",
            trigger: ":iframe .s_popup .s_banner",
            run: "click",
        },
        ...unfoldOptionsGroup("Popup"),
        {
            content: "Click on Display option",
            trigger:
                ".o_customize_tab [data-container-title='Popup'] [data-label='Display'] .dropdown-toggle",
            run: "click",
        },
        {
            content: "Click on the display 'On Click' option",
            trigger: ".o_popover [data-action-id='copyAnchor']",
            async run(helpers) {
                // Patch and ignore write on clipboard in tour as we don't have
                // permissions.
                browser.navigator.clipboard.writeText = () => {
                    console.info("Copy in clipboard ignored!");
                };
                await helpers.click();
            },
        },
        {
            content: "Check the copied anchor from the notification toast",
            trigger: ".o_notification_manager .o_notification_content",
            run() {
                // Cleanup the patched clipboard method
                browser.navigator.clipboard.writeText = oldWriteText;

                const notificationContent = this.anchor.innerText;
                const anchor = notificationContent.substring(notificationContent.indexOf("#"));

                if (anchor !== "#Win-%2420") {
                    console.error("The popup anchor is not '#Win-%2420' as expected.");
                }
            },
        },
        clickOnElement("button to close the popup", ":iframe .s_popup_close"),
        ...openLinkPopup({
            trigger: ":iframe .s_text_image a.btn-secondary",
            label: "Home",
            url: "#",
        }),
        clickOnElement("text image snippet button", ".o-we-linkpopover .o_we_edit_link"),
        {
            content: "Add a link to the popup in the URL input",
            trigger: ".o-we-linkpopover .o_we_href_input_link",
            run: "edit #Win-%2420",
        },
        ...clickOnSave(),
        {
            content: "Wait content of iframe is loaded",
            trigger: ":iframe main:contains(enhance your)",
        },
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
            trigger: ":iframe [data-view-xmlid='website.contactus']",
        },
        ...clickOnEditAndWaitEditMode(),
        ...insertSnippet({ id: "s_text_image", name: "Image - Text", groupName: "Content" }),
        {
            content: "Click on the text image snippet to edit it.",
            trigger: ":iframe .s_text_image",
            run: "click",
        },
        ...openLinkPopup({
            trigger: ":iframe .s_text_image a.btn-secondary",
            label: "Contact Us",
            url: "#",
        }),
        clickOnElement("text image snippet button", ".o-we-linkpopover .o_we_edit_link"),
        {
            content: "Add a link to the homepage in the URL input",
            trigger: ".o-we-linkpopover .o_we_href_input_link",
            run: "edit /#Win-%2420",
        },
        ...clickOnSave(),
        {
            content: "Wait content of iframe is loaded",
            trigger: ":iframe main:contains(enhance your)",
        },
        {
            content: "Wait form is patched",
            trigger: ":iframe form#contactus_form input[name=company]:value(yourcompany)",
        },
        clickOnElement("text image snippet button", ":iframe .s_text_image .btn-secondary"),
        {
            trigger: ":iframe [data-view-xmlid='website.homepage']",
        },
        {
            content: "Verify that the popup opens when the homepage page loads.",
            trigger: ":iframe .s_popup .modal[id='Win-%2420'].show",
        },
    ],
});
