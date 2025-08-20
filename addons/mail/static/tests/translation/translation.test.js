import { LONG_PRESS_DELAY } from "@mail/utils/common/hooks";
import {
    click,
    contains,
    defineMailModels,
    onRpcBefore,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { test } from "@odoo/hoot";
import { pointerDown } from "@odoo/hoot-dom";
import { advanceTime, mockTouch, mockUserAgent } from "@odoo/hoot-mock";
import { asyncStep, serverState, waitForSteps } from "@web/../tests/web_test_helpers";

defineMailModels();

test.tags("desktop");
test("Toggle display of original/translated version of chatter message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.message"].create({
        model: "res.partner",
        body: "Al mal tiempo, buena cara.",
        author_id: serverState.odoobotId,
        res_id: partnerId,
    });
    onRpcBefore("/mail/message/translate", () => {
        asyncStep("Request");
        return { body: "To bad weather, good face.", lang_name: "Spanish", error: null };
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains("[title='Translate']");
    await contains("[title='Revert']", { count: 0 });
    // Click acts as a toogle affecting its appearence and the actual message content displayed.
    await click("[title='Translate']");
    await contains(".o-mail-Message-body", {
        text: "To bad weather, good face.(Translated from: Spanish)",
    });
    await contains("[title='Translate']", { count: 0 });
    await contains("[title='Revert']");
    await click("[title='Revert']");
    await contains(".o-mail-Message", { text: "Al mal tiempo, buena cara." });
    await click("[title='Translate']");
    // The translation button should not trigger more than one external request for a single message.
    await waitForSteps(["Request"]);
});

test.tags("desktop");
test("translation of email message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.message"].create({
        model: "res.partner",
        body: "Al mal tiempo, buena cara.",
        message_type: "email",
        author_id: partnerId,
        res_id: partnerId,
    });
    onRpcBefore("/mail/message/translate", (args) => ({
        body: "To bad weather, good face.",
        lang_name: "Spanish",
        error: null,
    }));
    await start();
    await openFormView("res.partner", partnerId);
    await contains("span", {
        text: "Al mal tiempo, buena cara.",
        parent: [".o-mail-Message-body > div", { shadowRoot: true }],
    });
    await click("button[title='Expand']");
    await click(".o-dropdown-item:contains('Translate')");
    await contains("span", {
        text: "To bad weather, good face.",
        parent: [".o-mail-Message-body > div", { shadowRoot: true }],
    });
    await contains(".o-mail-Message-body", {
        text: "(Translated from: Spanish)",
    });
    await click("button[title='Expand']");
    await click(".o-dropdown-item:contains('Revert')");
    await contains("span", {
        text: "Al mal tiempo, buena cara.",
        parent: [".o-mail-Message-body > div", { shadowRoot: true }],
    });
});

test.tags("mobile");
test("Toggle message translation on mobile", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.message"].create({
        model: "res.partner",
        body: "Al mal tiempo, buena cara.",
        author_id: serverState.odoobotId,
        res_id: partnerId,
    });
    onRpcBefore("/mail/message/translate", () => ({
        body: "To bad weather, good face.",
        lang_name: "Spanish",
        error: null,
    }));
    mockTouch(true);
    mockUserAgent("Chrome/0.0.0 Android (OdooMobile; Linux; Android 13; Odoo TestSuite)");
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Message");
    await pointerDown(".o-mail-Message");
    await advanceTime(LONG_PRESS_DELAY);
    await click("button:contains('Translate')");
    await contains(".o-mail-Message-body", {
        text: "To bad weather, good face.(Translated from: Spanish)",
    });
});
