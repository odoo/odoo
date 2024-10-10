import { insertSnippet, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";
/**
 * The purpose of this tour is to check the Linktools to create a link to an
 * uploaded document.
 */
registerWebsitePreviewTour(
    "test_link_to_document",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            name: "Banner",
            id: "s_banner",
            groupName: "Intro",
        }),
        {
            content: "Click on button Start Now",
            trigger: ":iframe #wrap .s_banner a:nth-child(1)",
            run: "click",
        },
        {
            content: "Click on link to an uploaded document",
            trigger: ".o_url_input .o_we_user_value_widget.fa.fa-file",
            run: "click",
        },
        {
            content: "Click on the first file uploaded",
            trigger:
                ".o_select_media_dialog .o_we_documents .o_existing_attachment_cell:nth-child(1)",
            run: "click",
        },
        {
            content: "Check if a document link is created",
            trigger: ":iframe #wrap .s_banner .oe_edited_link[href^='/web/content']",
        },
        {
            content: "Check if by default the option auto-download is enabled",
            trigger: ":iframe #wrap .s_banner .oe_edited_link[href$='download=true']",
        },
        {
            content: "Deactivate direct download",
            trigger: ".o_switch > we-checkbox[name='direct_download']",
            run: "click",
        },
        {
            content: "Check if auto-download is disabled",
            trigger: ":iframe #wrap .s_banner .oe_edited_link:not([href$='download=true'])",
        },
    ]
);
