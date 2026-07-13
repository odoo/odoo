/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";

wTourUtils.registerWebsitePreviewTour("snippet_popup_esc", {
    test: true,
    url: "/",
    edition: true,
}, () => [
    wTourUtils.dragNDrop({id: "s_popup", name: "Popup"}),
    {
        content: "Remove the 'New customer' button so the popup has no focusable elements",
        trigger: "iframe .s_popup .btn-primary",
        run: function() {
            this.$anchor[0].remove();
        },
    },
    {
        content: "Click inside the popup to access its options",
        trigger: "iframe .s_popup .modal-content",
        run: "click",
    },
    {
        content: "Set delay to 0 so the popup appears immediately after save",
        trigger: 'we-input[data-attribute-name="showAfter"] input',
        run: "text 0",
    },
    ...wTourUtils.clickOnSave(),
    {
        content: "Wait for the popup to be displayed after save",
        trigger: "iframe .s_popup .modal.show",
        isCheck: true,
    },
    {
        content: "Press ESC to close the popup",
        trigger: "iframe .s_popup .modal",
        run: function() {
            this.$anchor[0].ownerDocument.activeElement.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "Escape" }));
        }
    },
    {
        content: "Verify the popup is closed",
        trigger: "iframe .s_popup .modal:not(.show)",
        isCheck: true,
    },
]);
