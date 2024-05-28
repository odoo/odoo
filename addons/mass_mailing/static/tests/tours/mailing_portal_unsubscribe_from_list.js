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
            trigger: "div#o_mailing_subscription_info span:contains('You have successfully unsubscribed from List1, List2')",
        }, {
            content: "Feedback textarea not displayed (see data)",
            trigger: "div#o_mailing_portal_subscription:not(textarea)",
        }, {
            content: "Choose 'Other' reason",
            trigger: "fieldset label:contains('Other')",
        }, {
            content: "Write feedback reason",
            trigger: "textarea[name='feedback']",
            run: "edit My feedback",
        }, {
            content: "Hit Send",
            trigger: "button#button_feedback",
        }, {
            content: "Confirmation feedback is sent",
            trigger: "div#o_mailing_subscription_feedback_info span:contains('Thank you for your feedback!')",
        }, {
            content: "Now exclude me",
            trigger: "div#button_blocklist_add",
        }, {
            content: "Confirmation exclusion is done",
            trigger: "div#o_mailing_subscription_update_info span:contains('Email added to our blocklist')",
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
            trigger: "div#o_mailing_subscription_info span:contains('You have successfully unsubscribed from List1, List2')",
        }, {
            content: "List1 is present, just opt-outed",
            trigger: "ul#o_mailing_subscription_form_lists li.list-group-item:contains('List1') span:contains('Off')",
            isCheck: true,
        }, {
            content: "List3 is present, opt-outed (test starting data)",
            trigger: "ul#o_mailing_subscription_form_lists li.list-group-item:contains('List3') span:contains('Off')",
            isCheck: true,
        }, {
            content: "List2 is proposed (not member -> proposal to join)",
            trigger: "ul#o_mailing_subscription_form_lists li.list-group-item:contains('List2')",
            isCheck: true,
        }, {
            content: "List4 is not proposed (not member but not public)",
            trigger: "ul#o_mailing_subscription_form_lists:not(:has(li.list-group-item:contains('List4')))",
            isCheck: true,
        }, {
            content: "Feedback textarea not displayed (see data)",
            trigger: "div#o_mailing_portal_subscription:not(textarea)",
        }, {
            content: "Choose 'Other' reason",
            trigger: "fieldset label:contains('Other')",
        }, {
            content: "Write feedback reason",
            trigger: "textarea[name='feedback']",
            run: "edit My feedback",
        }, {
            content: "Hit Send",
            trigger: "button#button_feedback",
        }, {
            content: "Confirmation feedback is sent",
            trigger: "div#o_mailing_subscription_feedback_info span:contains('Thank you for your feedback!')",
        }, {
            content: "Now exclude me",
            trigger: "div#button_blocklist_add",
        }, {
            content: "Confirmation exclusion is done",
            trigger: "div#o_mailing_subscription_update_info span:contains('Email added to our blocklist')",
        }, {
            content: "This should hide the subscription management panel",
            trigger: "body",
            run: function () {
                const elements = this.anchor.querySelectorAll('div#o_mailing_subscription_form_manage:has(.d-none)');
                if (elements.length === 1) {
                    this.anchor.classList.add('manage_panel_hidden');
                }
            },
        }, {
            content: "Verify previous step",
            trigger: "body.manage_panel_hidden",
            isCheck: true,
        }, {
            content: "Revert exclusion list",
            trigger: "div#button_blocklist_remove",
        }, {
            content: "Confirmation exclusion list is removed",
            trigger: "div#o_mailing_subscription_update_info span:contains('Email removed from our blocklist')",
        }, {
            content: "Choose the mailing list 3 to come back",
            trigger: "ul#o_mailing_subscription_form_lists input[title='List3']",
        }, {
            content: "List 3 is noted as subscribed again",
            trigger: "ul#o_mailing_subscription_form_lists li.list-group-item:contains('List3') span:contains('On')",
            isCheck: true,
        }, {
            content: "Add list 2",
            trigger: "ul#o_mailing_subscription_form_lists input[title='List2']",
        }, {
            content: "List 2 has joined the subscriptions",
            trigger: "ul#o_mailing_subscription_form_lists li.list-group-item:contains('List2') span:contains('On')",
            isCheck: true,
        }, {
            content: "List 3 is still noted as subscribed",
            trigger: "ul#o_mailing_subscription_form_lists li.list-group-item:contains('List3') span:contains('On')",
            isCheck: true,
        }, {
            content: "Feedback area is not displayed (nothing opt-out or no blocklist done, no feedback required)",
            trigger: "div#o_mailing_portal_subscription:not(textarea)",
            extra_trigger: "div#o_mailing_portal_subscription:not(fieldset)",
        }, {
            content: "Now exclude me (again)",
            trigger: "div#button_blocklist_add",
        }, {
            content: "Confirmation exclusion is done",
            trigger: "div#o_mailing_subscription_update_info span:contains('Email added to our blocklist')",
        }, {
            content: "Should display warning about marketing emails",
            trigger: "div#o_mailing_subscription_form_blocklisted p:contains('You will not receive marketing emails.')",
        }, {
            content: "Give a reason for blocklist (first one)",
            trigger: "fieldset input.o_mailing_subscription_opt_out_reason:first",
        }, {
            content: "Hit Send",
            trigger: "button#button_feedback",
        }, {
            content: "Confirmation feedback is sent",
            trigger: "div#o_mailing_subscription_feedback_info span:contains('Thank you for your feedback!')",
            isCheck: true,
        }
    ],
});
