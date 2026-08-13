/** @odoo-module **/

import { registry } from "@web/core/registry";

/*
 * Tour: use 'my' portal page of mailing to manage mailing lists subscription
 * as well as manage blocklist (add / remove my own email from block list).
 */
registry.category("web_tour.tours").add("mailing_portal_unsubscribe_from_my", {
    steps: () => [
        {
            content: "List1 is present, opt-in member",
            trigger:
                "ul#o_mailing_subscription_form_lists li.list-group-item:contains('List1') span:contains('Subscribed')",
            run: "click",
        },
        {
            content: "List3 is present, opt-outed (test starting data)",
            trigger:
                "ul#o_mailing_subscription_form_lists li.list-group-item:contains('List3') span:contains('Not subscribed')",
            run: "click",
        },
        {
            content: "List2 is proposed (not member -> proposal to join)",
            trigger:
                "ul#o_mailing_subscription_form_lists_additional li.list-group-item:contains('List2')",
            run: "click",
        },
        {
            content: "List4 is not proposed (not member but not private)",
            trigger:
                "ul#o_mailing_subscription_form_lists_additional:not(:has(li.list-group-item:contains('List4')))",
            run: "click",
        },
        {
            content: "List5 is not proposed (not member and not public)",
            trigger: "body:not(:has(li.list-group-item:contains('List5')))",
        },
        {
            trigger: "div#o_mailing_portal_subscription:not(fieldset)",
        },
        {
            content: "Feedback area is not displayed (nothing done, no feedback required)",
            trigger: "div#o_mailing_portal_subscription:not(textarea)",
            run: "click",
        },
        {
            content: "List3: come back (choose to opt-in instead of opt-out)",
            trigger: "ul#o_mailing_subscription_form_lists input[title='List3']",
            run: "click",
        },
        {
            content: "List2: join (opt-in, not already member)",
            trigger: "ul#o_mailing_subscription_form_lists_additional input[title='List2']",
            run: "click",
        },
        {
            content: "List1: opt-out",
            trigger: "ul#o_mailing_subscription_form_lists input[title='List1']",
            run: "click",
        },
        {
            content: "Update subscription",
            trigger: "button#button_form_send",
            run: "click",
        },
        {
            content: "Confirmation changes are done",
            trigger: "div#o_mailing_subscription_update_info span:contains('Membership updated')",
            run: "click",
        },
        {
            trigger: "div#o_mailing_portal_subscription:not(textarea)",
        },
        {
            content:
                "Should make feedback reasons choice appear (feedback still not displayed, linked to reasons)",
            trigger: "div#o_mailing_portal_subscription fieldset",
            run: "click",
        },
        {
            content: "Choose first reason, which should not display feedback (see data)",
            trigger: "fieldset input.o_mailing_subscription_opt_out_reason:first",
            run: "click",
        },
        {
            content: "Feedback textarea not displayed (see data)",
            trigger: "div#o_mailing_portal_subscription:not(textarea)",
            run: "click",
        },
        {
            content: "Choose 'Other' reason",
            trigger: "fieldset label:contains('Other')",
            run: "click",
        },
        {
            content: "This should display the Feedback area",
            trigger: "div#o_mailing_portal_subscription textarea",
        },
        {
            content: "Write feedback reason",
            trigger: "textarea[name='feedback']",
            run: "edit My feedback",
        },
        {
            content: "Hit Send",
            trigger: "button#button_feedback",
            run: "click",
        },
        {
            content: "Confirmation feedback is sent",
            trigger:
                "div#o_mailing_subscription_feedback_info span:contains('Sent. Thanks you for your feedback!')",
            run: "click",
        },
        {
            trigger: "textarea[disabled]",
        },
        {
            content: "Once sent feedback area is readonly",
            trigger: "fieldset input.o_mailing_subscription_opt_out_reason[disabled]",
        },
        {
            content: "Now exclude me",
            trigger: "div#button_blocklist_add",
            run: "click",
        },
        {
            content: "Confirmation exclusion is done",
            trigger:
                "div#o_mailing_subscription_update_info span:contains('Email added to our blocklist')",
            run: "click",
        },
        {
            content: "This should disable the 'Update my subscriptions' (Apply changes) button",
            trigger: "div#o_mailing_subscription_blocklist:not(button#button_form_send)",
        },
        {
            content: "This should enabled Feedback again",
            trigger: "div#o_mailing_portal_subscription textarea",
        },
        {
            content: "Display warning about mailing lists",
            trigger:
                "div#o_mailing_subscription_form_blocklisted p:contains('You will not receive any news from those mailing lists you are a member of')",
            run: "click",
        },
        {
            trigger: "div#o_mailing_subscription_form_blocklisted li strong:contains('List3')",
        },
        {
            content: "Warning should contain reference to memberships",
            trigger: "div#o_mailing_subscription_form_blocklisted li strong:contains('List2')",
            run: "click",
        },
        {
            content: "Give a reason for blocklist (first one)",
            trigger: "fieldset input.o_mailing_subscription_opt_out_reason:first",
            run: "click",
        },
        {
            content: "Hit Send",
            trigger: "button#button_feedback",
            run: "click",
        },
        {
            content: "Confirmation feedback is sent",
            trigger:
                "div#o_mailing_subscription_feedback_info span:contains('Sent. Thanks you for your feedback!')",
        },
    ],
});
