/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('mailing_portal_subscribe_to_public_list', {
    steps: () => [
        {
            content: "Public list is proposed to a portal user without a mailing contact",
            trigger: "ul#o_mailing_subscription_form_lists_additional li.list-group-item:contains('Public Mailing List')",
        }, {
            content: "Join the public list",
            trigger: "ul#o_mailing_subscription_form_lists_additional input[title='Public Mailing List']",
            run: "click",
        }, {
            content: "Apply subscription",
            trigger: "button#button_form_send",
            run: "click",
        }, {
            content: "Subscription is confirmed",
            trigger: "div#o_mailing_subscription_update_info span:contains('Membership updated')",
        },
    ],
});
