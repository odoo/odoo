/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";
import snippetNewsletterPopupUseTour from "@website_mass_mailing/../tests/tours/snippet_newsletter_popup_use";

wTourUtils.registerWebsitePreviewTour("snippet_newsletter_popup_edition", {
    test: true,
    url: "/",
    edition: true,
}, () => [
    wTourUtils.dragNDrop({
        id: 's_newsletter_subscribe_popup',
        name: 'Newsletter Popup',
    }),
    {
        content: "Check the modal is opened for edition",
        trigger: 'iframe .o_newsletter_popup .modal:visible',
        in_modal: false,
        run: () => null,
    },
    ...wTourUtils.clickOnSave(),
    {
        content: "Check the modal has been saved, closed",
        trigger: 'iframe body:has(.o_newsletter_popup)',
        run: snippetNewsletterPopupUseTour.ensurePopupNotVisible,
    }
]);
