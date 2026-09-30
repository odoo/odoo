import { registry } from "@web/core/registry";

/*
 * Tour: unsubscribe from a mailing done on lists (aka playing with opt-out flag
 * instead of directly blocking emails).
 */
registry.category("web_tour.tours").add("mailing_portal_unsubscribe_from_list", {
    steps: () => [
        {
            content: "Confirmation unsubscribe is done",
            trigger:
                "div#o_mailing_subscription_info span:contains('You are no longer part of the List1, List2 mailing list')",
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
            content: "Now exclude me",
            trigger: "div#button_blocklist_add",
            run: "click",
        },
        {
            content: "Confirmation exclusion is done",
            trigger:
                "div#o_mailing_subscription_update_info span:contains('Email added to our blocklist')",
        },
    ],
});

/*
 * Tour: unsubscribe from a mailing done on lists (aka playing with opt-out flag
 * instead of directly blocking emails), then play with list subscriptions and
 * blocklist addition / removal. This is mainly an extended version of the tour
 * hereabove, easing debug and splitting checks.
 */
registry.category("web_tour.tours").add("mailing_portal_unsubscribe_from_list_with_update", {
    steps: () => [
        {
            content: "Confirmation unsubscribe is done",
            trigger:
                "div#o_mailing_subscription_info span:contains('You are no longer part of the List1, List2 mailing list')",
            run: "click",
        },
        {
            content: "List1 is present, just opt-outed",
            trigger:
                "ul#o_mailing_subscription_form_lists li.list-group-item:contains('List1') span:contains('Not subscribed')",
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
            content: "Revert exclusion list",
            trigger: "div#button_blocklist_remove",
            run: "click",
        },
        {
            content: "Confirmation exclusion list is removed",
            trigger:
                "div#o_mailing_subscription_update_info span:contains('Email removed from our blocklist')",
            run: "click",
        },
        {
            content: "'Update my subscriptions' button usable again",
            trigger: "button#button_form_send:not([disabled])",
        },
        {
            content: "Choose the mailing list 3 to come back",
            trigger: "ul#o_mailing_subscription_form_lists input[title='List3']",
            run: "click",
        },
        {
            content: "Add list 2",
            trigger: "ul#o_mailing_subscription_form_lists_additional input[title='List2']",
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
            content: "List 3 is noted as subscribed again",
            trigger:
                "ul#o_mailing_subscription_form_lists li.list-group-item:contains('List3') span:contains('Subscribed')",
            run: "click",
        },
        {
            content: "List 2 has joined the subscriptions",
            trigger:
                "ul#o_mailing_subscription_form_lists li.list-group-item:contains('List2') span:contains('Subscribed')",
            run: "click",
        },
        {
            content: "No list in proposals",
            trigger:
                "div#o_mailing_subscription_form_manage:not(:has(ul#o_mailing_subscription_form_lists_additional))",
            run: "click",
        },
        {
            trigger: "div#o_mailing_portal_subscription:not(fieldset)",
        },
        {
            content:
                "Feedback area is not displayed (nothing opt-out or no blocklist done, no feedback required)",
            trigger: "div#o_mailing_portal_subscription:not(textarea)",
            run: "click",
        },
        {
            content: "Now exclude me (again)",
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
            content: "Should display warning about mailing lists",
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
