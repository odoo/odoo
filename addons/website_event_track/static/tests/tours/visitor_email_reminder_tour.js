/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('visitor_email_reminder_tour', {
    url: "/event/design-fair-los-angeles-1/agenda",
    steps: () => [
    {
        content: 'Click on favorite button',
        trigger: 'i[title="Set Favorite"]',
        run: 'click',
    },
    {
        content: 'Verification that the modal can be closed',
        trigger: '#email_reminder_form .o_form_button_cancel',
        run: 'click',
    },
    {
        content: 'Click on favorite button',
        trigger: 'i[title="Set Favorite"]',
        run: 'click',
    },
    {
        content: 'The form is filled',
        trigger: "#email_reminder_form input[name='email']",
        run: 'fill visitor@odoo.com',
    },
    {
        content: 'The form is submit',
        trigger: '#email_reminder_form button[type="submit"]',
        run: 'click',
    },
    {
        content: "Check if the notification is displayed.",
        trigger: 'div.o_send_email_reminder_success'
    }
]});