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
            trigger: "ul#o_mailing_subscription_form_lists li.list-group-item:contains('List1') span:contains('On')",
        },
        {
            content: "List3 is present, opt-outed (test starting data)",
            trigger: "ul#o_mailing_subscription_form_lists li.list-group-item:contains('List3') span:contains('Off')",
        },
        {
            content: "List2 is proposed (not member -> proposal to join)",
            trigger: "ul#o_mailing_subscription_form_lists li.list-group-item:contains('List2')",
        },
        {
            content: "List4 is not proposed (not member but not public)",
            trigger: "ul#o_mailing_subscription_form_lists:not(:has(li.list-group-item:contains('List4')))",
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
            content: "List 3 is noted as subscribed again",
            trigger: "ul#o_mailing_subscription_form_lists li.list-group-item:contains('List3') span:contains('On')",
        },
        {
            content: "List2: join (opt-in, not already member)",
            trigger: "ul#o_mailing_subscription_form_lists input[title='List2']",
            run: "click",
        },
        {
            content: "List 2 is noted as subscribed ",
            trigger: "ul#o_mailing_subscription_form_lists li.list-group-item:contains('List2') span:contains('On')",
        },
        {
            content: "List1: opt-out",
            trigger: "ul#o_mailing_subscription_form_lists input[title='List1']",
            run: "click",
        },
        {
            content: "List 1 is noted as unsubscribed ",
            trigger: "ul#o_mailing_subscription_form_lists li.list-group-item:contains('List1') span:contains('Off')",
        },
        {
            content: "Should not make feedback reasons choice appear",
            trigger: "body",
            run: function () {
                const elements = this.anchor.querySelectorAll('div#o_mailing_subscription_feedback:has(.d-none)');
                if (elements.length === 1) {
                    this.anchor.classList.add('feedback_panel_hidden');
                }
            },
        },
        {
            content: "Verify previous step",
            trigger: "body.feedback_panel_hidden",
        },
        {
            content: "Now exclude me",
            trigger: "div#button_blocklist_add",
            run: "click",
        },
        {
            content: "Confirmation exclusion is done",
            trigger: "div#o_mailing_subscription_update_info span:contains('Email added to our blocklist')",
        },
        {
            content: "This should hide the subscription management panel",
            trigger: "body",
            run: function () {
                const elements = this.anchor.querySelectorAll('div#o_mailing_subscription_form_manage:has(.d-none)');
                if (elements.length === 1) {
                    this.anchor.classList.add('manage_panel_hidden');
                }
            },
        },
        {
            content: "Verify previous step",
            trigger: "body.manage_panel_hidden",
        },
        {
            content: "This should show the feedback form",
            trigger: "body",
            run: function () {
                const elements = this.anchor.querySelectorAll('div#o_mailing_portal_subscription textarea');
                if (elements.length === 1) {
                    this.anchor.classList.add('feedback_enabled');
                }
            },
        },
        {
            content: "Verify previous step",
            trigger: "body.feedback_enabled",
        },
        {
            content: "Warning you will not receive anything anymore",
            trigger: "div#o_mailing_subscription_form_blocklisted p:contains('You will not receive marketing emails.')",
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
            trigger: "div#o_mailing_subscription_feedback_info span:contains('Thank you for your feedback!')",
        }
    ],
});
