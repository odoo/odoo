/** @odoo-module **/

import { registry } from "@web/core/registry";

/*
 * Tour: unsubscribe from a mailing done on documents (aka not on contacts or
 * mailing lists). We assume email is not member of any mailing list in this test.
 */
registry.category("web_tour.tours").add('mailing_portal_unsubscribe_from_document', {
    steps: () => [
        {
            content: "Confirmation unsubscribe is done",
            trigger: "div#o_mailing_subscription_info span:contains('You are no longer part of our services and will not be contacted again.')",
            run: "click",
        }, {
            content: "No warning should be displayed",
            trigger: "div#o_mailing_subscription_form_blocklisted:not(:has(p:contains('You will not receive any news from those mailing lists you are a member of')))",
            run: "click",
        }, {
            content: "Warning will not receive anything anymore",
            trigger: "div#o_mailing_subscription_form_blocklisted p:contains('You will not hear from us anymore.')",
            run: "click",
        }, {
            content: "Feedback textarea not displayed (see data)",
            trigger: "div#o_mailing_portal_subscription:not(textarea)",
            run: "click",
        }, {
            content: "Choose 'Other' reason",
            trigger: "fieldset label:contains('Other')",
            run: "click",
        }, {
            content: "This should display the Feedback area",
            trigger: "div#o_mailing_portal_subscription textarea",
        }, {
            content: "Write feedback reason",
            trigger: "textarea[name='feedback']",
            run: "edit My feedback",
        }, {
            content: "Hit Send",
            trigger: "button#button_feedback",
            run: "click",
        }, {
            content: "Confirmation feedback is sent",
            trigger: "div#o_mailing_subscription_feedback_info span:contains('Sent. Thanks you for your feedback!')",
            run: "click",
        }, {
            content: "Revert exclusion list",
            trigger: "div#button_blocklist_remove",
            run: "click",
        }, {
            content: "Confirmation exclusion list is removed",
            trigger: "div#o_mailing_subscription_update_info span:contains('Email removed from our blocklist')",
            run: "click",
        }, {
            content: "Now exclude me (again)",
            trigger: "div#button_blocklist_add",
            run: "click",
        }, {
            content: "Confirmation exclusion is done",
            trigger: "div#o_mailing_subscription_update_info span:contains('Email added to our blocklist')",
        },
    ],
});


/*
 * Tour: unsubscribe from a mailing done on documents (aka not on contacts or
 * mailing lists). We assume email is member of mailing lists in this test.
 */
registry.category("web_tour.tours").add('mailing_portal_unsubscribe_from_document_with_lists', {
    steps: () => [
        {
            content: "Confirmation unsubscribe is done",
            trigger: "div#o_mailing_subscription_info span:contains('You are no longer part of our services and will not be contacted again.')",
            run: "click",
        }, {
            content: "Display warning about mailing lists",
            trigger: "div#o_mailing_subscription_form_blocklisted p:contains('You will not receive any news from those mailing lists you are a member of')",
            run: "click",
        }, {
            content: "Warning should contain reference to memberships",
            trigger: "div#o_mailing_subscription_form_blocklisted li strong:contains('List1')",
            run: "click",
        }, {
            content: "Feedback textarea not displayed (see data)",
            trigger: "div#o_mailing_portal_subscription:not(textarea)",
            run: "click",
        }, {
            content: "Choose 'Other' reason",
            trigger: "fieldset label:contains('Other')",
            run: "click",
        }, {
            content: "This should display the Feedback area",
            trigger: "div#o_mailing_portal_subscription textarea",
        }, {
            content: "Write feedback reason",
            trigger: "textarea[name='feedback']",
            run: "edit My feedback",
        }, {
            content: "Hit Send",
            trigger: "button#button_feedback",
            run: "click",
        }, {
            content: "Confirmation feedback is sent",
            trigger: "div#o_mailing_subscription_feedback_info span:contains('Sent. Thanks you for your feedback!')",
            run: "click",
        }, {
            content: "Revert exclusion list",
            trigger: "div#button_blocklist_remove",
            run: "click",
        }, {
            content: "Confirmation exclusion list is removed",
            trigger: "div#o_mailing_subscription_update_info span:contains('Email removed from our blocklist')",
            run: "click",
        }, {
            content: "Now exclude me (again)",
            trigger: "div#button_blocklist_add",
            run: "click",
        }, {
            content: "Confirmation exclusion is done",
            trigger: "div#o_mailing_subscription_update_info span:contains('Email added to our blocklist')",
        },
    ],
});
