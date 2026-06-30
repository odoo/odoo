import {
    click,
    contains,
    defineMailModels,
    insertText,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

import { describe, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
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
    await contains(".o_last_breadcrumb_item", { text: "Jeanne" });
    await click("a", { text: "Admin" });
    await contains(".o_last_breadcrumb_item", { text: "Mitchell Admin" });
    // Assert 0 chat windows not sufficient because not enough time for potential chat window opening.
    // Let's open another chat window to give some time and assert only manually open chat window opens.
    await contains(".o-mail-ChatWindow", { count: 0 });
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button", { text: "New Message" });
    await insertText("input[placeholder='Search a conversation']", "abc");
    await click("a", { text: "Create Channel" });
    await contains(".o-mail-ChatWindow-header", { text: "abc" });
    await contains(".o-mail-ChatWindow", { count: 1 });
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
    await contains(".o_notification:contains(This conversation isn’t available.)");
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
    await contains(".o-mail-Message.o-highlighted:contains(Hello)");
    await animationFrame(); // give enough time for the potential breadcrumb item to render
    await contains(".breadcrumb-item", { count: 0 });
    await click("a.o_message_redirect:contains(Lena)");
    await contains(".o-mail-Message.o-highlighted:contains(Hey)");
    await contains(".breadcrumb-item:contains(Alice)");
});
