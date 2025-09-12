import { registry } from "@web/core/registry";

/*
 * Tour: use 'my' portal page of mailing to manage mailing lists subscription
 * as well as manage blocklist (add / remove my own email from block list).
 */
registry.category("web_tour.tours").add("mailing_portal_unsubscribe_from_my", {
    steps: () => [
        {
            content: "List1 is present, opt-in member",
            trigger: "ul#o_mailing_subscription_form_lists li.list-group-item:contains('List1') input:checked",
        },
        {
            content: "List3 is present, opt-outed (test starting data)",
            trigger: "ul#o_mailing_subscription_form_lists li.list-group-item:contains('List3') input:not(:checked)",
        },
        {
            content: "List2 is proposed (not member -> proposal to join)",
            trigger: "ul#o_mailing_subscription_form_lists li.list-group-item:contains('List2') input:not(:checked)",
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
            content: "Update Preferences",
            trigger: "#button_subscription_update_preferences",
            run: "click",
        },
        {
            content: "Check that subscriptions have been updated after the RPC call",
            trigger: "#o_mailing_subscription_update_info:visible",
            run: function (args = {}) {
                this.anchor.classList.add("d-none");
            }
        },
        {
            content: "List3 is noted as subscribed again",
            trigger: "ul#o_mailing_subscription_form_lists li.list-group-item:contains('List3') input:checked",
        },
        {
            content: "List2: join (opt-in, not already member)",
            trigger: "ul#o_mailing_subscription_form_lists input[title='List2']",
            run: "click",
        },
        {
            content: "Update Preferences",
            trigger: "#button_subscription_update_preferences",
            run: "click",
        },
        {
            content: "Check that subscriptions have been updated after the RPC call",
            trigger: "#o_mailing_subscription_update_info:visible",
            run: function () {
                // Make it invisible again to prevent future race conditions
                this.anchor.classList.add("d-none");
            }
        },
        {
            content: "List2 is noted as subscribed ",
            trigger: "ul#o_mailing_subscription_form_lists li.list-group-item:contains('List2') input:checked",
        },
        {
            content: "List1: opt-out",
            trigger: "ul#o_mailing_subscription_form_lists input[title='List1']",
            run: "click",
        },
        {
            content: "Update Preferences",
            trigger: "#button_subscription_update_preferences",
            run: "click",
        },
        {
            content: "Check that subscriptions have been updated after the RPC call",
            trigger: "#o_mailing_subscription_update_info:visible",
            run: function () {
                // Make it invisible again to prevent future race conditions
                this.anchor.classList.add("d-none");
            }
        },
        {
            content: "List1 is noted as unsubscribed ",
            trigger: "ul#o_mailing_subscription_form_lists li.list-group-item:contains('List1') input:not(:checked)",
        },
        {
            content: "Should not make feedback reasons choice appear",
            trigger: "div#o_mailing_subscription_feedback:not(:visible)",
            run: function () {
                document.querySelector("body").classList.add("feedback_panel_hidden");
            },
        },
        {
            content: "Now exclude me",
            trigger: "div#button_blocklist_add:not(.d-none)",
            run: "click",
        },
        {
            content: "Confirmation exclusion is done",
            trigger: "div#o_mailing_subscription_update_info span:contains('Email added to our blocklist')",
        },
        {
            content: "This should hide the subscription management panel",
            trigger: "div#o_mailing_subscription_form_manage:not(:visible)",
            run: function () {
                document.querySelector("body").classList.add("manage_panel_hidden");
            },
        },
        {
            content: "This should show the feedback form",
            trigger: "div#o_mailing_portal_subscription textarea:not(:visible)",
            run: function () {
                document.querySelector("body").classList.add("feedback_enabled");
            },
        },
        {
            content: "Warning you will not receive anything anymore",
            trigger: "div#o_mailing_subscription_form_blocklisted div:contains('You won't receive marketing emails.')",
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
        },
    ],
});
