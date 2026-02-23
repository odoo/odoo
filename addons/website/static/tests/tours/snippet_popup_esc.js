import {
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "snippet_popup_esc",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            name: "Popup",
            id: "s_popup",
            groupName: "Content",
        }),
        {
            content: "Click inside the popup to access its options",
            trigger: ":iframe .s_popup .modal-content .btn:contains('New customer')",
            run: "click",
        },
        {
            content: "Remove the 'New customer' button so the popup has no focusable elements",
            trigger: ".options-container[data-container-title=Button] [title='Remove this block']",
            run: "click",
        },
        {
            content: "Set delay to 0 so the popup appears immediately after save",
            trigger: '[data-label="Delay"] input',
            run: "edit 0",
        },
        ...clickOnSave(),
        {
            content: "Wait for the popup to be displayed after save",
            trigger: ":iframe .s_popup .modal",
            async run() {
                // Avoid race condition: wait for the fade in animation end,
                // otherwise escape is not taken into account.
                const { promise, resolve } = Promise.withResolvers();
                this.anchor.addEventListener("shown.bs.modal", resolve);
                await promise;
            },
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
    ]
);
