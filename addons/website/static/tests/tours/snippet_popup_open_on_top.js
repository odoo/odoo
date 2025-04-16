/** @odoo-module */

import wTourUtils from "website.tour_utils";

wTourUtils.registerWebsitePreviewTour("snippet_popup_open_on_top", {
    test: true,
    url: "/",
    edition: true,
}, [
    wTourUtils.dragNDrop({id: "s_popup", name: "Popup"}),
    {
        content: "Change content for long text.",
        trigger: "iframe .s_popup p.lead",
        run: 'text ' + ' hello world'.repeat(300),
    },
    {
        content: "Set delay to 0 second",
        trigger: '[data-attribute-name="showAfter"] input',
        run: 'text 0',
    },
    ...wTourUtils.clickOnSave(),
    {
        content: 'Check that the modal is scrolled on top',
        trigger: "iframe .s_popup .modal:contains('hello world')",
        run: function () {
            const modalEl = this.$anchor[0];
            if (modalEl.scrollHeight <= modalEl.clientHeight) {
                console.error('There is no scrollbar on the modal');
            }
            const activeEl = modalEl.ownerDocument.activeElement;
            if (activeEl.parentElement.closest('.modal') !== modalEl) {
                // Note: it might not be the best idea to still focus a button
                // that is not in the viewport, but since this is a niche case
                // this is the behavior right now. The important parts are:
                // in the normal case, focus the button; in all cases, the modal
                // should not be scrolled when opened.
                console.error('The focus should be on an element inside the modal');
            }
            if (modalEl.scrollTop !== 0) {
                console.error('The modal scrollbar is not scrolled at the top');
            }
        },
    },
]);
