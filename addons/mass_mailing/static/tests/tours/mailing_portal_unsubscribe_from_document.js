/** @odoo-module **/

import { registry } from "@web/core/registry";

/*
 * Tour: unsubscribe from a mailing done on documents (aka not on contacts or
 * mailing lists). We assume email is not member of any mailing list in this test.
 */
registry.category("web_tour.tours").add('mailing_portal_unsubscribe_from_document', {
    test: true,
    steps: () => [
        {
            content: "Confirmation unsubscribe is done",
            trigger: "div#subscription_info strong:contains('successfully unsubscribed')",
        }, {
            content: "No warning should be displayed",
            trigger: "div#div_blacklist:not(:has(p:contains('You were still subscribed to those newsletters. You will not receive any news from them anymore')))",
        }, {
            content: "Revert exclusion list",
            trigger: "div#button_remove_blacklist",
        }, {
            content: "Confirmation exclusion list is removed",
            trigger: "div#subscription_info strong:contains('removed from our blacklist')",
        }, {
            content: "Now exclude me (again)",
            trigger: "div#button_add_blacklist",
        }, {
            content: "Confirmation exclusion is done",
            trigger: "div#subscription_info strong:contains('added to our blacklist')",
            isCheck: true,
        },
    ],
});


/*
 * Tour: unsubscribe from a mailing done on documents (aka not on contacts or
 * mailing lists). We assume email is member of mailing lists in this test.
 */
registry.category("web_tour.tours").add('mailing_portal_unsubscribe_from_document_with_lists', {
    test: true,
    steps: () => [
        {
            content: "Confirmation unsubscribe is done",
            trigger: "div#subscription_info strong:contains('successfully unsubscribed')",
        }, {
            content: "Display warning about mailing lists",
            trigger: "div#div_blacklist p:contains('You were still subscribed to those newsletters. You will not receive any news from them anymore')",
        }, {
            content: "Warning should contain reference to memberships",
            trigger: "div#div_blacklist li strong:contains('List1')",
        }, {
            content: "Revert exclusion list",
            trigger: "div#button_remove_blacklist",
        }, {
            content: "Confirmation exclusion list is removed",
            trigger: "div#subscription_info strong:contains('removed from our blacklist')",
        }, {
            content: "Now exclude me (again)",
            trigger: "div#button_add_blacklist",
        }, {
            content: "Confirmation exclusion is done",
            trigger: "div#subscription_info strong:contains('added to our blacklist')",
            isCheck: true,
        },
    ],
});
