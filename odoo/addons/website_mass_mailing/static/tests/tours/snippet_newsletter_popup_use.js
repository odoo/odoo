/** @odoo-module **/

import { registry } from "@web/core/registry";

function ensurePopupNotVisible() {
    const $modal = this.$anchor.find('.o_newsletter_popup .modal');
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

registry.category("web_tour.tours").add('snippet_newsletter_popup_use', {
    test: true,
    url: '/',
    steps: () => [
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
        trigger: 'body:not(.modal-open)',
        run: ensurePopupNotVisible,
    }
]});

export default {
    ensurePopupNotVisible: ensurePopupNotVisible,
};
