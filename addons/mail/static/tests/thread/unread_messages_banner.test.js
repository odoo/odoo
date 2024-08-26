import {
    assertSteps,
    click,
    contains,
    defineMailModels,
    isInViewportOf,
    openDiscuss,
    scroll,
    start,
    startServer,
    step,
} from "@mail/../tests/mail_test_helpers";
import { Thread } from "@mail/core/common/thread";
import { describe, expect, test } from "@odoo/hoot";
import { queryFirst } from "@odoo/hoot-dom";
import { tick } from "@odoo/hoot-mock";
import {
    getService,
    patchWithCleanup,
    serverState,
    withUser,
} from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("show unread messages banner when there are unread messages", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    for (let i = 0; i < 30; ++i) {
        pyEnv["mail.message"].create({
            author_id: serverState.partnerId,
            body: `message ${i}`,
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", {
        text: "message 0",
    });
    await contains("span", { text: "30 new messagesMark as Read" });
});

test("mark thread as read from unread messages banner", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    for (let i = 0; i < 30; ++i) {
        pyEnv["mail.message"].create({
            author_id: serverState.partnerId,
            body: `message ${i}`,
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", {
        text: "message 0",
    });
    await click("span", {
        text: "Mark as Read",
        parent: ["span", { text: "30 new messagesMark as Read" }],
    });
    await contains(".o-mail-Thread-jumpToUnread", { count: 0 });
});

test("scroll to the first unread message (slow ref registration)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const messageIds = [];
    for (let i = 0; i < 201; i++) {
        messageIds.push(
            pyEnv["mail.message"].create({
                body: `message ${i}`,
                model: "discuss.channel",
                res_id: channelId,
            })
        );
    }
    const [selfMember] = pyEnv["discuss.channel.member"].search([
        ["partner_id", "=", serverState.partnerId],
        ["channel_id", "=", channelId],
    ]);
    pyEnv["discuss.channel.member"].write([selfMember], { new_message_separator: messageIds[100] });
    let slowRegisterMessageRef = false;
    patchWithCleanup(Thread.prototype, {
        async registerMessageRef() {
            if (slowRegisterMessageRef) {
                // Ensure scroll is made even when messages are mounted later.
                await new Promise((res) => setTimeout(res, 500));
            }
            super.registerMessageRef(...arguments);
        },
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Jump to Present']");
    await scroll(".o-mail-Thread", "bottom");
    await contains(".o-mail-Thread", { scroll: "bottom" });
    slowRegisterMessageRef = true;
    await click("span", {
        text: "101 new messages",
        parent: ["span", { text: "101 new messagesMark as Read" }],
    });
    document.addEventListener("scrollend", () => step("scrollend"), { capture: true });
    // 1. scroll top, 2. scroll to the unread message 3. slight scroll when highlight ends.
    await assertSteps(["scrollend", "scrollend", "scrollend"]);
    const thread = document.querySelector(".o-mail-Thread");
    const message = queryFirst(".o-mail-Message:contains(message 100)");
    expect(isInViewportOf(thread, message)).toBe(true);
});

test("scroll to unread notification", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const bobPartnerId = pyEnv["res.partner"].create({ name: "Bob" });
    const bobUserId = pyEnv["res.users"].create({ name: "Bob", partner_id: bobPartnerId });
    let lastMessageId;
    for (let i = 0; i < 60; ++i) {
        lastMessageId = pyEnv["mail.message"].create({
            author_id: serverState.partnerId,
            body: `message ${i}`,
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    const [memberId] = pyEnv["discuss.channel.member"].search([
        ["partner_id", "=", serverState.partnerId],
        ["channel_id", "=", channelId],
    ]);
    pyEnv["discuss.channel.member"].write([memberId], { new_message_separator: lastMessageId + 1 });
    await start();
    await withUser(bobUserId, () => {
        getService("orm").call("discuss.channel", "add_members", [[channelId]], {
            partner_ids: [bobPartnerId],
        });
    });
    await openDiscuss(channelId);
    await contains(".o-mail-Thread-newMessage ~ .o-mail-NotificationMessage", {
        text: "Bob joined the channel",
    });
    await tick(); // wait for the scroll to first unread to complete
    document.addEventListener("scrollend", () => step("scrollend"), { capture: true });
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await assertSteps(["scrollend"]);
    await scroll(".o-mail-Thread", 0);
    await assertSteps(["scrollend"]);
    const thread = document.querySelector(".o-mail-Thread");
    const message = queryFirst(".o-mail-NotificationMessage:contains(Bob joined the channel)");
    expect(isInViewportOf(thread, message)).toBe(false);
    await click("span", {
        text: "1 new message",
        parent: ["span", { text: "1 new messageMark as Read" }],
    });
    await assertSteps(["scrollend"]);
    expect(isInViewportOf(thread, message)).toBe(true);
});
