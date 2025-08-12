import {
    insertSnippet,
    clickOnSave,
    clickOnEditAndWaitEditMode,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

registerWebsitePreviewTour("snippet_visibility_option", {
    url: "/",
    edition: true,
}, () => [
    ...insertSnippet({
        id: "s_popup",
        name: "Popup",
        groupName: "Content",
    }),
    {
        content: "Click on the column within the popup snippet.",
        trigger: ":iframe #wrap .s_popup .o_cc1",
        run: "click"
    },
    {
        content: "Click the 'No Desktop' visibility option.",
        trigger: "[data-container-title='Column'] [data-action-param='no_desktop']",
        run: "click"
    },
    {
        content: "Click on the banner within the popup snippet.",
        trigger: ":iframe #wrap .s_popup .s_banner",
        run: "click"
    },
    {
        content: "Click the 'No Desktop' visibility option.",
        trigger: "[data-container-title='Block'] [data-action-param='no_desktop']",
        run: "click"
    },
    {
        content: "Click on the popup snippet to hide",
        trigger: ".o_we_invisible_root_parent",
        run: "click"
    },
    {
        content: "Click on the popup snippet in the list of invisible elements.",
        trigger: ".o_we_invisible_root_parent",
        run: "click"
    },
    {
        content: "Check that only the banner is marked as invisible and the column entry does not appear in the panel.",
        trigger: "li > .o_we_invisible_entry",
        run: () => {
            const isBlockInvisible = document.querySelector("li .o_we_invisible_entry i").classList.contains("fa-eye-slash");
            const isColumnEntryDisplayed = document.querySelector("li li .o_we_invisible_entry");
            if (!isBlockInvisible || !!isColumnEntryDisplayed) {
                console.error("Visibility issue detected with the elements.");
            }
        }
    },
    ...clickOnSave(),
    ...clickOnEditAndWaitEditMode(),
    {
        content: "Check that only the popup entry is displayed and that it is invisible.",
        trigger: ".o_we_invisible_root_parent",
        run: () => {
            const isSubentryDisplayed = document.querySelector("li .o_we_invisible_entry");
            const isPopupInvisible = document.querySelector(".o_we_invisible_root_parent > i").classList.contains("fa-eye-slash");
            if (!!isSubentryDisplayed || !isPopupInvisible) {
                console.error("Visibility issue detected with the elements.");
            }
        }
    },
    {
        content: "Click on the popup entry to show it.",
        trigger: ".o_we_invisible_root_parent",
        run: "click"
    },
    {
        content: "Click on the banner entry to show it.",
        trigger: "li > .o_we_invisible_entry",
        run: "click"
    },
    {
        content: "Check that the popup and banner are visible and the column is still invisible.",
        trigger: "li li > .o_we_invisible_entry",
        run: () => {
            const isPopupVisible = document.querySelector(".o_we_invisible_root_parent i").classList.contains("fa-eye");
            const isBannerVisible = document.querySelector("li .o_we_invisible_entry i").classList.contains("fa-eye");
            const isColumnInvisible = document.querySelector("li li .o_we_invisible_entry i").classList.contains("fa-eye-slash");
            if (!isPopupVisible || !isBannerVisible || !isColumnInvisible) {
                console.error("Visibility issue detected with the elements.");
            }
        }
    },
    {
        content: "Click on the popup entry to hide it.",
        trigger: ".o_we_invisible_root_parent",
        run: "click",
    },
    {
        content: "Check that only the popup entry is displayed and that it is invisible.",
        trigger: ".o_we_invisible_root_parent",
        run: () => {
            const isSubentryDisplayed = document.querySelector("li .o_we_invisible_entry");
            const isPopupInvisible = document.querySelector(".o_we_invisible_root_parent > i").classList.contains("fa-eye-slash");
            if (!!isSubentryDisplayed || !isPopupInvisible) {
                console.error("Visibility issue detected with the elements.");
            }
        }
    },
    {
        content: "Click on the popup entry to show it.",
        trigger: ".o_we_invisible_root_parent",
        run: "click",
    },
    {
        content: "Check that the popup and banner are visible and the column is still invisible.",
        trigger: "li > .o_we_invisible_entry",
        run: () => {
            const isPopupVisible = document.querySelector(".o_we_invisible_root_parent i").classList.contains("fa-eye");
            const isBannerVisible = document.querySelector("li .o_we_invisible_entry i").classList.contains("fa-eye");
            const isColumnInvisible = document.querySelector("li li .o_we_invisible_entry i").classList.contains("fa-eye-slash");
            if (!isPopupVisible || !isBannerVisible || !isColumnInvisible) {
                console.error("Visibility issue detected with the elements.");
            }
        }
    },
]);
