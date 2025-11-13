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
            content: "Click the 'No Desktop' visibility option to hide the banner.",
            trigger: `.options-container [data-label="Visibility"] button[data-action-param="no_desktop"]`,
            run: "click",
        },
        {
            content: "Check that the popup is visible.",
            trigger: ".o_we_invisible_root_parent i.fa-eye",
        },
        {
            content: "Check that the banner is invisible.",
            trigger: "ul .o_we_invisible_entry i.fa-eye-slash",
        },
    ]
);
