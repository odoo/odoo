/* @odoo-module */

import { registry } from "@web/core/registry";

/**
 * This tour depends on data created by python test in charge of launching it.
 * It is not intended to work when launched from interface. It is needed to test
 * an action (action manager) which is not possible to test with QUnit.
 * @see mail_enterprise/tests/test_discuss_channel_expand.py
 */
registry
    .category("web_tour.tours")
    .add("mail_enterprise/static/tests/tours/discuss_channel_expand_test_tour.js", {
        test: true,
        steps: () => [
            {
                content:
                    "Click on 'Open Actions Menu' in the chat window header to show expand button",
                trigger:
                    '.o-mail-ChatWindow:contains("test-mail-channel-expand-tour") [title="Open Actions Menu"]',
            },
            {
                content: "Click on expand button to open channel in Discuss",
                trigger:
                    '.o-mail-ChatWindow:contains("test-mail-channel-expand-tour") [title="Open in Discuss"]',
            },
            {
                content:
                    "Check that first message of #test-mail-channel-expand-tour is shown in Discuss app",
                trigger:
                    '.o-mail-Discuss-content .o-mail-Message-body:contains("test-message-mail-channel-expand-tour")',
                run: () => {},
            },
        ],
    });
