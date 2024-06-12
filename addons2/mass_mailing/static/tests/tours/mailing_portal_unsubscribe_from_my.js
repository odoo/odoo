/** @odoo-module **/

import { registry } from "@web/core/registry";

/*
 * Tour: use 'my' portal page of mailing to manage mailing lists subscription
 * as well as manage blocklist (add / remove my own email from block list).
 */
registry.category("web_tour.tours").add('mailing_portal_unsubscribe_from_my', {
    test: true,
    steps: () => [
       {
            content: "List1 is present, opt-in member",
            trigger: "ul#o_mailing_subscription_form_lists li.list-group-item:contains('List1') span:contains('Subscribed')",
        }, {
            content: "List3 is present, opt-outed (test starting data)",
            trigger: "ul#o_mailing_subscription_form_lists li.list-group-item:contains('List3') span:contains('Not subscribed')",
        }, {
            content: "List2 is proposed (not member -> proposal to join)",
            trigger: "ul#o_mailing_subscription_form_lists_additional li.list-group-item:contains('List2')",
        }, {
            content: "List4 is not proposed (not member but not private)",
            trigger: "ul#o_mailing_subscription_form_lists_additional:not(:has(li.list-group-item:contains('List4')))",
        }, {
            content: "Feedback area is not displayed (nothing done, no feedback required)",
            trigger: "div#o_mailing_portal_subscription:not(textarea)",
            extra_trigger: "div#o_mailing_portal_subscription:not(fieldset)",
        }, {
            content: "List3: come back (choose to opt-in instead of opt-out)",
            trigger: "ul#o_mailing_subscription_form_lists input[title='List3']",
        }, {
            content: "List2: join (opt-in, not already member)",
            trigger: "ul#o_mailing_subscription_form_lists_additional input[title='List2']",
        }, {
            content: "List1: opt-out",
            trigger: "ul#o_mailing_subscription_form_lists input[title='List1']",
        }, {
            content: "Update subscription",
            trigger: "button#button_form_send",
        }, {
            content: "Confirmation changes are done",
            trigger: "div#o_mailing_subscription_update_info span:contains('Membership updated')",
        }, {
            content: "Should make feedback reasons choice appear (feedback still not displayed, linked to reasons)",
            trigger: "div#o_mailing_portal_subscription fieldset",
            extra_trigger: "div#o_mailing_portal_subscription:not(textarea)",
        }, {
            content: "Choose first reason, which should not display feedback (see data)",
            trigger: "fieldset input.o_mailing_subscription_opt_out_reason:first",
        }, {
            content: "Feedback textarea not displayed (see data)",
            trigger: "div#o_mailing_portal_subscription:not(textarea)",
        }, {
            content: "Choose 'Other' reason",
            trigger: "fieldset label:contains('Other')",
        }, {
            content: "This should display the Feedback area",
            trigger: "div#o_mailing_portal_subscription textarea",
            isCheck: true,
        }, {
            content: "Write feedback reason",
            trigger: "textarea[name='feedback']",
            run: "text My feedback",
        }, {
            content: "Hit Send",
            trigger: "button#button_feedback",
        }, {
            content: "Confirmation feedback is sent",
            trigger: "div#o_mailing_subscription_feedback_info span:contains('Sent. Thanks you for your feedback!')",
        }, {
            content: "Once sent feedback area is readonly",
            trigger: "fieldset input.o_mailing_subscription_opt_out_reason[disabled]",
            extra_trigger: "textarea[disabled]",
            isCheck: true,
        }, {
            content: "Now exclude me",
            trigger: "div#button_blocklist_add",
        }, {
            content: "Confirmation exclusion is done",
            trigger: "div#o_mailing_subscription_update_info span:contains('Email added to our blocklist')",
        }, {
            content: "This should disable the 'Update my subscriptions' (Apply changes) button",
            trigger: "div#o_mailing_subscription_blocklist:not(button#button_form_send)",
            isCheck: true,
        }, {
            content: "This should enabled Feedback again",
            trigger: "div#o_mailing_portal_subscription textarea",
            isCheck: true,
        }, {
            content: "Display warning about mailing lists",
            trigger: "div#o_mailing_subscription_form_blocklisted p:contains('You will not receive any news from those mailing lists you are a member of')",
        }, {
            content: "Warning should contain reference to memberships",
            trigger: "div#o_mailing_subscription_form_blocklisted li strong:contains('List2')",
            extra_trigger: "div#o_mailing_subscription_form_blocklisted li strong:contains('List3')",
        }, {
            content: "Give a reason for blocklist (first one)",
            trigger: "fieldset input.o_mailing_subscription_opt_out_reason:first",
        }, {
            content: "Hit Send",
            trigger: "button#button_feedback",
        }, {
            content: "Confirmation feedback is sent",
            trigger: "div#o_mailing_subscription_feedback_info span:contains('Sent. Thanks you for your feedback!')",
            isCheck: true,
        }
    ],
});
