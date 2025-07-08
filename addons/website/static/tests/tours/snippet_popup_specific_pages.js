import { stepUtils } from "@web_tour/tour_utils";
import {
    changeOptionInPopover,
    clickOnEditAndWaitEditMode,
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

const selectPage = (page, url, position = 1) => [
    {
        content: `Enter '${page}' in dropdown.`,
        trigger: '.we-bg-options-container [data-label=" "] input:not(:disabled)',
        run: `edit ${page}`,
    },
    {
        content: "Verify autocomplete popover is displayed.",
        trigger: ".o_website_ui_autocomplete",
    },
    {
        content: `Select '${page}' from dropdown.`,
        trigger: `.o_website_ui_autocomplete > li.ui-autocomplete-item:nth-child(${position}) a`,
        run: "click",
    },
    {
        content: `Verify '${page}' is selected.`,
        trigger: `.we-bg-options-container .o-hb-input-base:disabled[data-name='${url}']`,
    },
];

const navigateAndVerify = (label, xmlid, triggerSelector = null) => [
    {
        content: `Go to ${label} page`,
        trigger: triggerSelector || `:iframe .nav-item a:contains("${label}")`,
        run: "click",
    },
    {
        content: `Verify that we are on ${label} page`,
        trigger: `:iframe [data-view-xmlid='website.${xmlid}']`,
        timeout: 30000,
    },
];

const checkPopup = (shouldExist, label) => ({
    content: `Check popup ${shouldExist ? "exists" : "does not exist"} on ${label} page.`,
    trigger: `:iframe #o_shared_blocks:${
        shouldExist ? "has" : "not(:has"
    }([data-snippet='s_popup']:not(:visible))`,
});

registerWebsitePreviewTour(
    "snippet_popup_specific_pages",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({ name: "Popup", id: "s_popup", groupName: "Content" }),
        {
            content: "Click on the Popup snippet to edit it.",
            trigger: ":iframe #wrap.o_editable [data-snippet='s_popup']:not(:visible)",
            run: "click",
        },
        ...changeOptionInPopover("Popup", "Show on", "These specific pages"),
        ...clickOnSave(),
        checkPopup(true, "Home"),
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Toggle the visibility of the Popup",
            trigger: '.o_we_invisible_el_panel .o_we_invisible_entry:contains("Popup")',
            run: "click",
        },
        ...changeOptionInPopover("Popup", "Show on", "These specific pages"),
        ...selectPage("contactus", "/contactus", 1),
        ...clickOnSave(),
        ...navigateAndVerify(
            "Contact us",
            "contactus",
            ":iframe .navbar-nav a.btn-primary[href='/contactus']:nth-child(1)"
        ),
        checkPopup(true, "Contact us"),
        ...navigateAndVerify("Home", "homepage"),
        stepUtils.waitIframeIsReady(),
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Toggle the visibility of the Popup",
            trigger: '.o_we_invisible_el_panel .o_we_invisible_entry:contains("Popup")',
            run: "click",
        },
        {
            content: "Remove Home page ('/') from the selection.",
            trigger: ".we-bg-options-container button.fa-minus:nth-child(1)",
            run: "click",
        },
        {
            content: "Verify Home page ('/') is removed from the selection.",
            trigger:
                ".we-bg-options-container .o-hb-input-base:not(:has(:disabled[data-name='/']))",
        },
        ...clickOnSave(),
        ...navigateAndVerify("Home", "homepage"),
        checkPopup(false, "Home"),
        ...navigateAndVerify(
            "Contact us",
            "contactus",
            ":iframe .navbar-nav a.btn-primary[href='/contactus']:nth-child(1)"
        ),
        checkPopup(true, "Contact us"),
    ]
);
