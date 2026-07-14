/** @odoo-module **/

import {
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour("snippet_popup_esc", {
    url: "/",
    edition: true,
}, () => [
    ...insertSnippet({
        name: "Popup",
        id: "s_popup",
        groupName: "Content",
    }),
    {
        content: "Remove the 'New customer' button so the popup has no focusable elements",
        trigger: ":iframe .s_popup .btn-primary",
        run: function() {
            this.anchor.remove();
        },
    },
    {
        content: "Click inside the popup to access its options",
        trigger: ":iframe .s_popup .modal-content",
        run: "click",
    },
    {
        content: "Set delay to 0 so the popup appears immediately after save",
        trigger: '[data-attribute-name="showAfter"] input',
        run: "edit 0",
    },
    ...clickOnSave(),
    {
        content: "Wait for the popup to be displayed after save",
        trigger: ":iframe .s_popup .modal.show",
    },
    {
        content: "Press ESC to close the popup",
        trigger: ":iframe",
        run: "press Escape",
    },
    {
        content: "Verify the popup is closed",
        trigger: ":iframe .s_popup .modal:not(.show)",
    },
]);
