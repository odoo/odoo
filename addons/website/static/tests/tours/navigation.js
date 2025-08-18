import { stepUtils } from "@web_tour/tour_service/tour_utils";
import { insertSnippet, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "website_editing_awaits_navigation",
    {
        url: "/",
    },
    () => [
        {
            content: "Navigate to the 'Contact Us' page",
            trigger: ":iframe .top_menu a[href='/contactus']:not(:visible)",
            run: "click",
        },
        {
            content: "Click on Edit right after that",
            trigger: ".o_menu_systray_item.o_edit_website_container > button",
            run: "click",
        },
        stepUtils.waitIframeIsReady(),
        {
            content: "Contact us page appears first before the builder sidebar",
            trigger: ":iframe section h1:contains('Contact Us'), :not(.o-website-builder_sidebar)",
        },
        {
            content: "Can insert a snippet",
            trigger: ".o-website-builder_sidebar",
        },
        ...insertSnippet({
            id: "s_banner",
            name: "Banner",
            groupName: "Intro",
        }),
        {
            content: "",
            trigger: ":iframe section.s_banner",
        },
    ]
);
