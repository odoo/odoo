import { expect, test } from "@odoo/hoot";
import { mockUserAgent } from "@odoo/hoot-mock";
import {
    assertSteps,
    click,
    contains,
    defineMailModels,
    onRpcBefore,
    openFormView,
    start,
    startServer,
    step,
} from "@mail/../tests/mail_test_helpers";
import { serverState } from "@web/../tests/web_test_helpers";

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
        step("Request");
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
    await assertSteps(["Request"]);
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
    onRpcBefore("/mail/message/translate", (args) => {
        return { body: "To bad weather, good face.", lang_name: "Spanish", error: null };
    });
    await start();
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

test.tags("desktop");
test("Do not show translate action if message body is empty", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const subtypeId = pyEnv["mail.message.subtype"].create({ description: "Task created" });
    const attachmentId = pyEnv["ir.attachment"].create({
        mimetype: "text/plain",
        name: "Blah.txt",
    });
    pyEnv["mail.message"].create([
        {
            model: "res.partner",
            body: '<div summary="o_mail_notification"><p>Not Empty</p></div>',
            message_type: "notification",
            res_id: partnerId,
            subtype_id: subtypeId,
        },
        {
            attachment_ids: [attachmentId],
            model: "res.partner",
            res_id: partnerId,
        },
        {
            model: "res.partner",
            body: "Not Empty",
            res_id: partnerId,
        },
    ]);
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Message", { count: 3 });
    expect("button[title='Expand']").toHaveCount(0);
    expect(".o-mail-Message:eq(0) [title='Translate']").toHaveCount(1);
    expect(".o-mail-Message:eq(1) [title='Translate']").toHaveCount(0);
    expect(".o-mail-Message:eq(2) [title='Translate']").toHaveCount(0);
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
    onRpcBefore("/mail/message/translate", () => {
        return { body: "To bad weather, good face.", lang_name: "Spanish", error: null };
    });
    mockUserAgent("android");
    await start();
    await openFormView("res.partner", partnerId);
    await click("button[title='Expand']");
    await click("span", { text: "Translate" });
    await contains(".o-mail-Message-body", {
        text: "To bad weather, good face.(Translated from: Spanish)",
    });
});
