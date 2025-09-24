import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    clickOnSnippet,
    insertSnippet,
    goBackToBlocks,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";
import { stepUtils } from "@web_tour/tour_utils";

const cover = {
    id: "s_cover",
    name: "Cover",
    groupName: "Intro",
};

registerWebsitePreviewTour(
    "website_click_tour",
    {
        url: "/",
    },
    () => [
        stepUtils.waitIframeIsReady(),
        {
            content: "trigger a page navigation",
            trigger: ':iframe a[href="/contactus"]',
            run: "click",
        },
        {
            content: "wait for the page to be loaded",
            trigger: ".o_website_preview :iframe [data-view-xmlid='website.contactus']",
        },
        ...clickOnEditAndWaitEditMode(),
        {
            content: "click on a link that would trigger navigation",
            trigger: ':iframe a[href="/"]',
            run: "click",
        },
        {
            content: "click the User dropdown to show Log out button",
            trigger: ":iframe .dropdown:has(#o_logout) > a",
            run: "click",
        },
        {
            content:
                "click the Log out button and expect not to be logged out during the following steps",
            trigger: ":iframe .editor_enable #o_logout",
            run: "click",
        },
        goBackToBlocks(),
        ...insertSnippet(cover),
        ...clickOnSnippet(cover),
        ...clickOnSave(),
    ]
);
