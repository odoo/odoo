/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains } from "@web/../tests/utils";

QUnit.module("Google Cloud Translation");

QUnit.test("Toggle display of original/translated version of chatter message", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.message"].create({
        model: "res.partner",
        body: "Al mal tiempo, buena cara.",
        author_id: pyEnv.odoobotId,
        res_id: partnerId,
    });
    const { openFormView } = await start({
        mockRPC(route) {
            if (route === "/mail/message/translate") {
                assert.step("Request");
                return { body: "To bad weather, good face.", lang_name: "Spanish", error: null };
            }
        },
    });
    await openFormView("res.partner", partnerId);
    await click("button[title='Expand']");
    await contains("span[title='Translate']");
    await contains("span[title='Revert']", { count: 0 });
    // Click acts as a toogle affecting its appearence and the actual message content displayed.
    await click("span[title='Translate']");
    await click("button[title='Expand']");
    await contains(".o-mail-Message-body", {
        text: "To bad weather, good face.(Translated from: Spanish)",
    });
    await contains("span[title='Translate']", { count: 0 });
    await contains("span[title='Revert']");
    await click("span[title='Revert']");
    await click("button[title='Expand']");
    await contains(".o-mail-Message", {
        text: "Al mal tiempo, buena cara.",
    });
    await click("span[title='Translate']");
    // The translation button should not trigger more than one external request for a single message.
    assert.verifySteps(["Request"]);
});

QUnit.test("translation of email message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.message"].create({
        model: "res.partner",
        body: "Al mal tiempo, buena cara.",
        message_type: "email",
        author_id: partnerId,
        res_id: partnerId,
    });
    const { openFormView } = await start({
        mockRPC(route) {
            if (route === "/mail/message/translate") {
                return { body: "To bad weather, good face.", lang_name: "Spanish", error: null };
            }
        },
    });
    await openFormView("res.partner", partnerId);
    await contains("span", {
        text: "Al mal tiempo, buena cara.",
        parent: [".o-mail-Message-body > div", { shadowRoot: true }],
    });
    await click("button[title='Expand']");
    await click("span[title='Translate']");
    await contains("span", {
        text: "To bad weather, good face.",
        parent: [".o-mail-Message-body > div", { shadowRoot: true }],
    });
    await contains(".o-mail-Message-body", {
        text: "(Translated from: Spanish)",
    });
    await click("button[title='Expand']");
    await click("span[title='Revert']");
    await contains("span", {
        text: "Al mal tiempo, buena cara.",
        parent: [".o-mail-Message-body > div", { shadowRoot: true }],
    });
});
