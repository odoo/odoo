/** @odoo-module */

import wTourUtils from "website.tour_utils";

wTourUtils.registerWebsitePreviewTour("website_popup_visibility_option", {
    test: true,
    edition: true,
    url: "/",
}, [
    wTourUtils.dragNDrop({
        id: "s_popup",
        name: "Popup",
    }),
    {
        content: "Click on the column within the popup snippet.",
        trigger: "iframe #wrap .s_popup .o_cc1",
    },
    {
        content: "Click the 'No Desktop' visibility option.",
        trigger: ".snippet-option-DeviceVisibility we-button[data-toggle-device-visibility='no_desktop']",
    },
    {
        content: "Verify that the popup is visible and the column is invisible.",
        trigger: ".o_we_invisible_root_parent i.fa-eye, ul .o_we_invisible_entry i.fa-eye-slash",
    },
]);
