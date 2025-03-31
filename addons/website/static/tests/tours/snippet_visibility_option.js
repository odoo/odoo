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
        trigger: ".snippet-option-DeviceVisibility we-button[data-toggle-device-visibility='no_desktop']",
        run: "click"
    },
    {
        content: "Click on the banner within the popup snippet.",
        trigger: ":iframe #wrap .s_popup .s_banner",
        run: "click"
    },
    {
        content: "Click the 'No Desktop' visibility option.",
        trigger: "we-button[data-toggle-device-visibility='no_desktop']",
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
        content: "Verify that both the banner and column are marked as invisible.",
        trigger: ".o_we_invisible_root_parent",
        run: () => {
            const isBlockInvisible = document.querySelector("li .o_we_invisible_entry i").classList.contains("fa-eye-slash");
            const isColumnInvisible = document.querySelector("li li .o_we_invisible_entry i").classList.contains("fa-eye-slash");
            if (!isBlockInvisible || !isColumnInvisible) {
                console.error("Visibility issue detected with the elements.");
            }
        }
    },
    ...clickOnSave(),
    ...clickOnEditAndWaitEditMode(),
    {
        content: "Click on the banner snippet in the list of invisible elements.",
        trigger: "li > .o_we_invisible_entry",
        run: "click"
    },
    {
        content: "Verify that the popup is visible and the column is still invisible.",
        trigger: "li > .o_we_invisible_entry",
        run: () => {
            const isPopupVisible = document.querySelector(".o_we_invisible_root_parent i").classList.contains("fa-eye");
            const isColumnInvisible = document.querySelector("li li .o_we_invisible_entry i").classList.contains("fa-eye-slash");
            if (!isPopupVisible || !isColumnInvisible) {
                console.error("Visibility issue detected with the elements.");
            }
        }
    },
    ...clickOnSave(),
    ...clickOnEditAndWaitEditMode(),
    {
        content: "Click on the column snippet in the list of invisible elements.",
        trigger: "li li .o_we_invisible_entry",
        run: "click"
    },
    {
        content: "Verify that both the popup and the banner are now visible.",
        trigger: ".o_we_invisible_root_parent",
        run: () => {
            const isPopupVisible = document.querySelector(".o_we_invisible_root_parent i").classList.contains("fa-eye");
            const isBlockVisible = document.querySelector("li .o_we_invisible_entry i").classList.contains("fa-eye");
            if (!isPopupVisible || !isBlockVisible) {
                console.error("Visibility issue detected with the elements.");
            }
        }
    },
    {
        content: "Click on the popup snippet to hide its descendant elements.",
        trigger: ".o_we_invisible_root_parent",
        run: () => {
            setTimeout(() => {
                document.querySelector(".o_we_invisible_root_parent").click();
            }, 1000);
        }
    },
    {
        content: "Make sure the parent snippet is invisible.",
        trigger: ".o_we_invisible_root_parent i.fa-eye-slash",
    },
    {
        content: "Verify that both the banner and column snippets are marked as invisible.",
        trigger: ".o_we_invisible_root_parent",
        run: () => {
            const isBlockInvisible = document.querySelector("li .o_we_invisible_entry i").classList.contains("fa-eye-slash");
            const isColumnInvisible = document.querySelector("li li .o_we_invisible_entry i").classList.contains("fa-eye-slash");
            if (!isColumnInvisible || !isBlockInvisible) {
                console.error("Visibility issue detected with the elements.");
            }
        }
    },
]);
