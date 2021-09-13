/** @odoo-module */

import wTourUtils from "website.tour_utils";

wTourUtils.registerWebsitePreviewTour("snippet_popup_display_on_click", {
    test: true,
    url: "/",
    edition: true,
}, [
    wTourUtils.dragNDrop({id: "s_text_image", name: "Image - Text"}),
    wTourUtils.dragNDrop({id: "s_popup", name: "Popup"}),
    {
        content: "Click inside the popup to access its options menu.",
        in_modal: false,
        trigger: "iframe .s_popup .s_banner",
    },
    wTourUtils.changeOption("SnippetPopup", 'we-select[data-attribute-name="display"] we-toggler'),
    {
        content: "Click on the display 'On Click' option",
        trigger: "#oe_snippets we-button[data-name='onclick_opt']",
        in_modal: false,
        run() {
            // The clipboard cannot be accessed from a script.
            // https://w3c.github.io/editing/docs/execCommand/#dfn-the-copy-command
            // The execCommand is patched for that step so that ClipboardJS still
            // sends the "success" event.
            const oldExecCommand = document.execCommand;
            document.execCommand = () => true;
            this.$anchor[0].click();
            document.execCommand = oldExecCommand;
        }
    },
    {
        content: "Check the copied anchor from the notification toast",
        trigger: ".o_notification_manager .o_notification_content",
        run() {
            const notificationContent = this.$anchor[0].innerText;
            const anchor = notificationContent.substring(notificationContent.indexOf("#"));

            if (anchor !== "#Win-%2420") {
                console.error("The popup anchor is not '#Win-%2420' as expected.");
            }
        },
    },
    wTourUtils.clickOnElement("button to close the popup", "iframe .s_popup_close"),
    wTourUtils.clickOnElement("text image snippet button", "iframe .s_text_image .btn-primary"),
    {
        content: "Paste the popup anchor in the URL input",
        trigger: "#o_link_dialog_url_input",
        run: "text #Win-%2420"
    },
    ...wTourUtils.clickOnSave(),
    wTourUtils.clickOnElement("text image snippet button", "iframe .s_text_image .btn-primary"),
    {
        content: "Verify that the popup opens after clicked the button.",
        in_modal: false,
        trigger: "iframe .s_popup .modal[id='Win-%2420'].show",
    },
    wTourUtils.clickOnElement("button to close the popup", "iframe .s_popup_close"),
    {
        content: "Go to the 'contactus' page.",
        trigger: "iframe a[href='/contactus']",
    },
    {
        content: "wait for the page to be loaded",
        trigger: ".o_website_preview[data-view-xmlid='website.contactus']",
        run: () => null, // it"s a check
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    wTourUtils.dragNDrop({id: "s_text_image", name: "Image - Text"}),
    wTourUtils.clickOnElement("text image snippet button", "iframe .s_text_image .btn-primary"),
    {
        content: "Add a link to the homepage popup in the URL input",
        trigger: "#o_link_dialog_url_input",
        run: "text /#Win-%2420"
    },
    ...wTourUtils.clickOnSave(),
    wTourUtils.clickOnElement("text image snippet button", "iframe .s_text_image .btn-primary"),
    {
        content: "Verify that the popup opens when the homepage page loads.",
        in_modal: false,
        extra_trigger: ".o_website_preview[data-view-xmlid='website.homepage']",
        trigger: "iframe .s_popup .modal[id='Win-%2420'].show",
    },
]);
