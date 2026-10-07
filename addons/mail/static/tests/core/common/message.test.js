import {
    click,
    contains,
    defineMailModels,
    insertText,
    openFormView,
    openMessagingMenu,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";

import { describe, test } from "@odoo/hoot";
import { animationFrame, waitFor, waitForNone } from "@odoo/hoot-dom";
import { getOrigin } from "@web/core/utils/urls";

describe.current.tags("desktop");
defineMailModels();

test("following internal link from chatter does not open chat window", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Jeanne" });
    pyEnv["mail.message"].create({
        body: `Created by <a href="#" data-oe-model="res.partner" data-oe-id="${pyEnv.user.partner_id}">Admin</a>`,
        model: "res.partner",
        res_id: partnerId,
    });
    await start();
    await openFormView("res.partner", partnerId);
    await waitFor(".o_last_breadcrumb_item:has(:text('Jeanne')):count(1)");
    await click("a:text('Admin')");
    await waitFor(".o_last_breadcrumb_item:has(:text('Mitchell Admin')):count(1)");
    // Assert 0 chat windows not sufficient because not enough time for potential chat window opening.
    // Let's open another chat window to give some time and assert only manually open chat window opens.
    await waitForNone(".o-mail-ChatWindow");
    await openMessagingMenu();
    await triggerHotkey("control+k");
    await insertText(".o_command_palette_search input[placeholder='Search for a command...'", "@");
    await insertText(".o_command_palette_search input[placeholder='Search conversations'", "abc");
    await click("a:has(:text('Create Channel'))");
    await click("button:text(Create Channel)");
    await waitFor(".o-mail-ChatWindow-header:text('abc'):count(1)");
    await waitFor(".o-mail-ChatWindow:count(1)");
});

test("message link shows error when the message is not known", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Alice" });
    const url = `${getOrigin()}/mail/message/999999`;
    pyEnv["mail.message"].create({
        body: `Check this out <a class="o_message_redirect" href="${url}" data-oe-model="mail.message" data-oe-id="999999">${url}</a>`,
        model: "res.partner",
        res_id: partnerId,
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click("a.o_message_redirect");
    await waitFor(".o_notification:contains(This conversation isn’t available.):count(1)");
});

test("same-thread message link does not open the thread again but highlights the message", async () => {
    const pyEnv = await startServer();
    const [aliceId, lenaId] = pyEnv["res.partner"].create([{ name: "Alice" }, { name: "Lena" }]);
    const helloMessageId = pyEnv["mail.message"].create({
        body: "Hello",
        model: "res.partner",
        res_id: aliceId,
    });
    const heyMessageId = pyEnv["mail.message"].create({
        body: "Hey",
        model: "res.partner",
        res_id: lenaId,
    });
    const helloUrl = `${getOrigin()}/mail/message/${helloMessageId}`;
    pyEnv["mail.message"].create({
        body: `Check this out <a class="o_message_redirect" href="${helloUrl}" data-oe-model="mail.message" data-oe-id="${helloMessageId}">${helloUrl}</a>`,
        model: "res.partner",
        res_id: aliceId,
    });
    const heyUrl = `${getOrigin()}/mail/message/${heyMessageId}`;
    pyEnv["mail.message"].create({
        body: `Another thread <a class="o_message_redirect" href="${heyUrl}" data-oe-model="mail.message" data-oe-id="${heyMessageId}">${heyUrl}</a>`,
        model: "res.partner",
        res_id: aliceId,
    });
    await start();
    await openFormView("res.partner", aliceId);
    await click("a.o_message_redirect:contains(Alice)");
    await waitFor(".o-mail-Message.o-highlighted:contains(Hello):count(1)");
    await animationFrame(); // give enough time for the potential breadcrumb item to render
    await waitForNone(".breadcrumb-item");
    await click("a.o_message_redirect:contains(Lena)");
    await waitFor(".o-mail-Message.o-highlighted:contains(Hey):count(1)");
    await waitFor(".breadcrumb-item:contains(Alice):count(1)");
});

test("code block embedded in an email message's body should be ignored", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Jeanne" });
    pyEnv["mail.message"].create({
        body: `<pre data-embedded="readonlySyntaxHighlighting" data-language-id="python">print('hello')</pre>`,
        message_type: "email",
        model: "res.partner",
        res_id: partnerId,
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(
        "pre[data-embedded='readonlySyntaxHighlighting']:not([data-embedded-mounted]):text(print('hello'))",
        { parent: [".o-mail-Message-shadowBody", { shadowRoot: true }] }
    );
});
