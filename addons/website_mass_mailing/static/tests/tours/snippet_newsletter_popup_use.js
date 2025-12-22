/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('snippet_newsletter_popup_use', {
    url: '/',
    steps: () => [
    {
        content: "Check the modal is not yet opened and force it opened",
        trigger: 'body:has(.o_newsletter_popup:not(:visible) .modal)',
    },
    {
        content: "Check the modal is now opened and enter text in the subscribe input",
        trigger: '.o_newsletter_popup .modal.modal_shown input',
        run: "edit hello@world.com",
    },
    {
        content: "Subscribe",
        trigger: '.modal.modal_shown.show .btn-primary:contains(subscribe)',
        run: "click",
    },
    {
        content: "Check the modal is now closed",
        trigger: 'body:has(.o_newsletter_popup:not(:visible) .modal)',
    }
]});
