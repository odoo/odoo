/** @odoo-module **/

import { registry } from "@web/core/registry";

/*
 * Tour: unsubscribe from a mailing done on lists (aka playing with opt-out flag
 * instead of directly blocking emails).
 */
registry.category("web_tour.tours").add('mailing_portal_unsubscribe_from_list', {
    test: true,
    steps: () => [
        {
            content: "Confirmation unsubscribe is done",
            trigger: "div#o_mailing_subscription_info_state strong:contains('unsubscribed from List1, List2')",
        }, {
            content: "Write feedback reason",
            trigger: "textarea[name='feedback']",
            run: "text My feedback",
        }, {
            content: "Hit Send",
            trigger: "div#button_feedback",
        }, {
            content: "Confirmation feedback is sent",
            trigger: "div#o_mailing_subscription_info_state:contains('Thanks for your feedback')",
        }, {
            content: "Now exclude me",
            trigger: "div#button_blocklist_add",
        }, {
            content: "Confirmation exclusion is done",
            trigger: "div#o_mailing_subscription_info_state strong:contains('added to our blocklist')",
            isCheck: true,
        },
    ],
});


/*
 * Tour: unsubscribe from a mailing done on lists (aka playing with opt-out flag
 * instead of directly blocking emails), then play with list subscriptions and
 * blocklist addition / removal. This is mainly an extended version of the tour
 * hereabove, easing debug and splitting checks.
 */
registry.category("web_tour.tours").add('mailing_portal_unsubscribe_from_list_with_update', {
    test: true,
    steps: () => [
        {
            content: "Confirmation unsubscribe is done",
            trigger: "div#o_mailing_subscription_info_state strong:contains('unsubscribed from List1, List2')",
        }, {
            content: "List1 is present, just opt-outed",
            trigger: "li.list-group-item:contains('List1') span:contains('Unsubscribed')",
        }, {
            content: "List3 is present, opt-outed (test starting data)",
            trigger: "li.list-group-item:contains('List3') span:contains('Unsubscribed')",
        }, {
            content: "List2 is not present (not member -> not displayed)",
            trigger: "ul:not(:has(li.list-group-item:contains('List2') span:contains('Unsubscribed')))",
        }, {
            content: "Write feedback reason",
            trigger: "textarea[name='feedback']",
            run: "text My feedback",
        }, {
            content: "Hit Send",
            trigger: "div#button_feedback",
        }, {
            content: "Confirmation feedback is sent",
            trigger: "div#o_mailing_subscription_info_state:contains('Thanks for your feedback')",
        }, {
            content: "Now exclude me",
            trigger: "div#button_blocklist_add",
        }, {
            content: "Confirmation exclusion is done",
            trigger: "div#o_mailing_subscription_info_state strong:contains('added to our blocklist')",
        }, {
            content: "This should disable the 'Update my subscriptions' button",
            trigger: "button#button_form_send[disabled]",
            isCheck: true,
        }, {
            content: "Revert exclusion list",
            trigger: "div#button_blocklist_remove",
        }, {
            content: "Confirmation exclusion list is removed",
            trigger: "div#o_mailing_subscription_info_state strong:contains('removed from our blocklist')",
        },  {
            content: "'Update my subscriptions' button usable again",
            trigger: "button#button_form_send:not([disabled])",
        }, {
            content: "Choose the mailing list 3 to come back",
            trigger: "li.list-group-item:contains('List3') input",
        }, {
            content: "Update subscription",
            trigger: "button#button_form_send",
        }, {
            content: "Confirmation changes are done",
            trigger: "div#o_mailing_subscription_info_state strong:contains('updated your memberships')",
        }, {
            content: "Now exclude me (again)",
            trigger: "div#button_blocklist_add",
        }, {
            content: "Confirmation exclusion is done",
            trigger: "div#o_mailing_subscription_info_state strong:contains('added to our blocklist')",
            isCheck: true,
        }
    ],
});
