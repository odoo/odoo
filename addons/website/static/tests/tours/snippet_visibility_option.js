import wTourUtils from '@website/js/tours/tour_utils';

wTourUtils.registerWebsitePreviewTour("snippet_visibility_option", {
    test: true,
    url: '/',
    edition: true,
}, () => [
    ...wTourUtils.dragNDrop({
        id: 's_popup',
        name: 'Popup',
    }),
    {
        content: "Select the inner column of the popup.",
        trigger: ":iframe #wrap .s_popup .s_banner",
        run: "click"
    },
    {
        content: "Click on the 'Invisible on Desktop' button.",
        trigger: "we-button[data-toggle-device-visibility='no_desktop']",
        run: "click"
    },
    {
        content: "Click on the block's invisible element entry.",
        trigger: "li > .o_we_invisible_entry",
        run: "click"
    },
    {
        content: "Verify the visibility status of the block and popup.",
        trigger: "li > .o_we_invisible_entry",
        run: () => {
            const isParentVisible = document.querySelector(".o_we_invisible_root_parent i").classList.contains("fa-eye");
            if (!isParentVisible) {
                console.error("There is a visibility issue with the element.");
            }
        }
    },
    {
        content: "Click on the popup's visible element entry.",
        trigger: ".o_we_invisible_root_parent",
        run: "click"
    },
    {
        content: "Verify the invisibility status of the block and popup.",
        trigger: ".o_we_invisible_root_parent",
        run: () => {
            const isChildInvisible = document.querySelector("li > .o_we_invisible_entry i").classList.contains("fa-eye-slash");
            if (!isChildInvisible) {
                console.error("There is a visibility issue with the element.");
            }
        }
    },
]);
