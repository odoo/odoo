/** @odoo-module **/

import wTourUtils from "website.tour_utils";
import newsletterPopupUseTour from "website_mass_mailing.tour.newsletter_popup_use";

wTourUtils.registerWebsitePreviewTour("newsletter_popup_edition", {
    test: true,
    url: "/",
    edition: true,
}, [
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
        extra_trigger: 'iframe body:not(.editor_enable)',
        run: newsletterPopupUseTour.ensurePopupNotVisible,
    }
]);
