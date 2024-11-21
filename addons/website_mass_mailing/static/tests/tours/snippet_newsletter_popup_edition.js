/** @odoo-module **/

import {
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';
import snippetNewsletterPopupUseTour from "@website_mass_mailing/../tests/tours/snippet_newsletter_popup_use";

registerWebsitePreviewTour("snippet_newsletter_popup_edition", {
    url: "/",
    edition: true,
}, () => [
    ...insertSnippet({
        id: 's_newsletter_subscribe_popup',
        name: 'Newsletter Popup',
        groupName: "Contact & Forms",
    }),
    {
        content: "Check the modal is opened for edition",
        trigger: ':iframe .o_newsletter_popup .modal:visible',
    },
    ...clickOnSave(),
    {
        content: "Check the modal has been saved, closed",
        trigger: ':iframe body:has(.o_newsletter_popup)',
        run: snippetNewsletterPopupUseTour.ensurePopupNotVisible,
    }
]);
