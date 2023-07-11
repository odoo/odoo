odoo.define("website_mass_mailing.tour.newsletter_popup_edition", function (require) {
"use strict";

const tour = require('web_tour.tour');
const wTourUtils = require('website.tour_utils');
const newsletterPopupUseTour = require('website_mass_mailing.tour.newsletter_popup_use');

tour.register('newsletter_popup_edition', {
    test: true,
    url: '/?enable_editor=1',
}, [
    wTourUtils.dragNDrop({
        id: 's_newsletter_subscribe_popup',
        name: 'Newsletter Popup',
    }),
    {
        content: "Check the modal is opened for edition",
        trigger: '.o_newsletter_popup .modal:visible',
        in_modal: false,
        run: () => null,
    },
    ...wTourUtils.clickOnSave(),
    {
        content: "Check the modal has been saved, closed",
        trigger: 'body:has(.o_newsletter_popup)',
        extra_trigger: 'body:not(.editor_enable)',
        run: newsletterPopupUseTour.ensurePopupNotVisible,
    }
]);
});

odoo.define("website_mass_mailing.tour.newsletter_popup_use", function (require) {
"use strict";

const tour = require('web_tour.tour');

function ensurePopupNotVisible() {
    const $modal = $('.o_newsletter_popup .modal');
    if ($modal.length !== 1) {
        // Avoid the tour to succeed if the modal can't be found while
        // it should. Indeed, if the selector ever becomes wrong and the
        // expected element is actually not found anymore, the test
        // won't be testing anything anymore as the visible check will
        // always be truthy on empty jQuery element.
        console.error("Modal couldn't be found in the DOM. The tour is not working as expected.");
    }
    if ($modal.is(':visible')) {
        console.error('Modal should not be opened.');
    }
}

tour.register('newsletter_popup_use', {
    test: true,
    url: '/',
}, [
    {
        content: "Check the modal is not yet opened and force it opened",
        trigger: 'body:has(.o_newsletter_popup)',
        run: ensurePopupNotVisible,
    },
    {
        content: "Check the modal is now opened and enter text in the subscribe input",
        trigger: '.o_newsletter_popup .modal input',
        in_modal: false,
        run: 'text hello@world.com',
    },
    {
        content: "Subscribe",
        trigger: '.modal-dialog .btn-primary',
    },
    {
        content: "Check the modal is now closed",
        trigger: 'body:has(.o_newsletter_popup)',
        run: ensurePopupNotVisible,
    }
]);

return {
    ensurePopupNotVisible: ensurePopupNotVisible,
};
});
