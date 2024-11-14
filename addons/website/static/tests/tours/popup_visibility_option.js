import { insertSnippet, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "website_popup_visibility_option",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_popup",
            name: "Popup",
            groupName: "Content",
        }),
        {
            content: "Click on the column within the popup snippet.",
            trigger: ":iframe #wrap .s_popup .o_cc1",
            run: "click",
        },
        {
            content: "Click the 'No Desktop' visibility option.",
            trigger:
                ".snippet-option-DeviceVisibility we-button[data-toggle-device-visibility='no_desktop']",
            run: "click",
        },
        {
            content: "Verify that the popup is visible and the column is invisible.",
            trigger:
                ".o_we_invisible_root_parent i.fa-eye, ul .o_we_invisible_entry i.fa-eye-slash",
        },
    ]
);
