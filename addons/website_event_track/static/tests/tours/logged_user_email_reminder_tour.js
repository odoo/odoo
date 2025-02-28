/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('logged_user_email_reminder_tour', {
    steps: () => [
    {
        content: 'Click on favorite button',
        trigger: 'i[title="Set Favorite"]',
        run: 'click',
    },
    {
        content: "Check if the notification is displayed.",
        trigger: 'div.o_send_email_reminder_success',
    }
]});
