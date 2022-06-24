odoo.define("website_mass_mailing.tour.newsletter_popup_edition", function (require) {
"use strict";

const tour = require('web_tour.tour');
const wTourUtils = require('website.tour_utils');

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
        trigger: 'iframe .o_newsletter_popup .modal:visible',
        in_modal: false,
        run: () => null,
    },
    ...wTourUtils.clickOnSave(),
    {
        content: "Check the modal has been saved, closed",
        trigger: 'iframe .o_newsletter_popup',
        extra_trigger: 'iframe body:not(.editor_enable)',
        run: function (actions) {
            const $modal = this.$anchor.find('.modal');
            if ($modal.is(':visible')) {
                console.error('Modal is still opened...');
            }
        },
    },
]);
});

odoo.define("website_mass_mailing.tour.newsletter_popup_use", function (require) {
"use strict";

const tour = require('web_tour.tour');

tour.register('newsletter_popup_use', {
    test: true,
    url: '/',
}, [
    {
        content: "Check the modal is not yet opened and force it opened",
        trigger: '.o_newsletter_popup',
        run: function (actions) {
            const $modal = this.$anchor.find('.modal');
            if ($modal.is(':visible')) {
                console.error('Modal is already opened...');
            }
            $(document).trigger('mouseleave');
        },
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
        trigger: '.o_newsletter_popup',
        run: function (actions) {
            const $modal = this.$anchor.find('.modal');
            if ($modal.is(':visible')) {
                console.error('Modal is still opened...');
            }
        },
    }
]);
});
