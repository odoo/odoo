import {
    click,
    contains,
    defineMailModels,
    dragenterFiles,
    insertText,
    isInViewportOf,
    listenStoreFetch,
    openDiscuss,
    openFormView,
    openMessagingMenu,
    scroll,
    start,
    startServer,
    waitStoreFetch,
    MENU_ACTIVE_IDS,
} from "@mail/../tests/mail_test_helpers";
import { mail_store } from "@mail/../tests/mock_server/mail_mock_server";
import { Store } from "@mail/../tests/mock_server/store";

import { Message } from "@mail/core/common/message_model";
import { Thread } from "@mail/core/common/thread";
import { UseForwardRefsToParent } from "@mail/utils/common/hooks";

import { describe, expect, test } from "@odoo/hoot";
import {
    advanceFrame,
    advanceTime,
    animationFrame,
    press,
    queryFirst,
    queryOne,
    waitFor,
    waitForNone,
} from "@odoo/hoot-dom";
import { mockDate, tick } from "@odoo/hoot-mock";
import {
    Command,
    getService,
    MockServer,
    onRpc,
    serverState,
    withUser,
} from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";

import { rpc } from "@web/core/network/rpc";
import { range } from "@web/core/utils/numbers";

describe.current.tags("desktop");
defineMailModels();

test("messages still render when thread is reloaded twice in a row", async () => {
    // Two reloads in quick succession (e.g. overlapping jumps to present) must
    // not leave the message list stuck on the empty phantom view. The component
    // mirrors `thread.isLoaded` into `state.mountedAndLoaded`, and the second
    // reload landing while the first mirror update is still being applied used
    // to strand `mountedAndLoaded` at false, so no message was ever rendered.
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
    });
    pyEnv["mail.message"].create({
        body: "Hello",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Message:count(1)");
    const thread = getService("mail.store")["discuss.channel"].get(channelId);
    thread.isLoaded = false;
    thread.isLoaded = true;
    await advanceFrame(1);
    thread.isLoaded = false;
    thread.isLoaded = true;
    await advanceFrame(1);
    await animationFrame();
    await waitFor(".o-mail-Message:count(1)");
});

test("messages still render when a reset strands mountedAndLoaded", async () => {
    // Regression for runbot 940032. `reset()` forces `mountedAndLoaded` false;
    // the mirror effect only re-syncs it to `isLoaded` on a patch. A reset
    // landing while `mountedAndLoaded` is already false (e.g. an out-of-render-
    // cycle `applyScroll` from a late image load) used to schedule no patch,
    // because `resetCount` was not reactive, stranding `mountedAndLoaded` at
    // false so the empty phantom rendered no message. Here `applyScroll` is
    // neutralized so nothing else re-syncs, and the flag is forced false to
    // hold the strand deterministically.
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
    });
    pyEnv["mail.message"].create({
        body: "Hello",
        model: "discuss.channel",
        res_id: channelId,
    });
    let thread;
    patch(Thread.prototype, {
        setup() {
            super.setup();
            thread = this;
        },
        applyScroll() {},
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Message:count(1)");
    thread.state.mountedAndLoaded = false;
    await advanceFrame(1);
    await waitForNone(".o-mail-Message");
    thread.reset();
    await advanceFrame(1);
    await animationFrame();
    await waitFor(".o-mail-Message:count(1)");
});

test("dragover files on thread with composer", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        group_public_id: false,
        name: "General",
    });
    const text3 = new File(["hello, world"], "text3.txt", { type: "text/plain" });
    await start();
    await openDiscuss(channelId);
    await dragenterFiles(".o-mail-Thread", [text3]);
    await waitFor(".o-Dropzone:count(1)");
});

test("load more messages from channel (auto-load on scroll)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        group_public_id: false,
        name: "General",
    });
    let newestMessageId;
    for (let i = 0; i <= 60; i++) {
        newestMessageId = pyEnv["mail.message"].create({
            body: i.toString(),
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    const [selfMember] = pyEnv["discuss.channel.member"].search_read([
        ["partner_id", "=", serverState.partnerId],
        ["channel_id", "=", channelId],
    ]);
    pyEnv["discuss.channel.member"].write([selfMember.id], {
        new_message_separator: newestMessageId + 1,
    });
    await start();
    await openDiscuss(channelId);
    await contains("button:text(Load More)", { before: [".o-mail-Message", { count: 30 }] });
    expect(getComputedStyle(queryOne("button:text(Load More)")).opacity).toBe("1");
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await scroll(".o-mail-Thread", 0);
    await waitFor(".o-mail-Message:count(60)");
    await contains(".o-mail-Message:has(:text('30'))", {
        after: [".o-mail-Message:has(:text('29'))"],
    });
});

test("show message subject when subject is not the same as the thread name", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        group_public_id: false,
        name: "General",
    });
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
        subject: "Salutations, voyageur",
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(
        ".o-mail-Message:has(:text('Subject: Salutations, voyageur not empty')):count(1)"
    );
});

test("do not show message subject when subject is the same as the thread name", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        group_public_id: false,
        name: "Salutations, voyageur",
    });
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
        subject: "Salutations, voyageur",
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Message:has(:text('not empty')):count(1)");
    await waitForNone(".o-mail-Message:has(:text('Subject: Salutations, voyageur not empty'))");
});

test("auto-scroll to last read message on thread load", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const messageIds = [];
    for (let i = 0; i <= 200; i++) {
        messageIds.push(
            pyEnv["mail.message"].create({
                body: `message ${i}`,
                model: "discuss.channel",
                res_id: channelId,
            })
        );
    }
    const [selfMemberId] = pyEnv["discuss.channel.member"].search([
        ["partner_id", "=", serverState.partnerId],
        ["channel_id", "=", channelId],
    ]);
    pyEnv["discuss.channel.member"].write([selfMemberId], {
        new_message_separator: messageIds[100],
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Thread-newMessage ~ .o-mail-Message:has(:text('message 100')):count(1)");
    await isInViewportOf(".o-mail-Message:has(:text('message 100'))", ".o-mail-Thread");
});

test("auto-scroll on thread load when last read is a hidden notification", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const messageIds = [];
    for (let i = 0; i <= 200; i++) {
        messageIds.push(
            pyEnv["mail.message"].create({
                body: `message ${i}`,
                message_type: i === 100 ? "notification" : "comment",
                model: "discuss.channel",
                res_id: channelId,
            })
        );
    }
    const [selfMemberId] = pyEnv["discuss.channel.member"].search([
        ["partner_id", "=", serverState.partnerId],
        ["channel_id", "=", channelId],
    ]);
    pyEnv["discuss.channel.member"].write([selfMemberId], {
        new_message_separator: messageIds[100],
    });
    // Simulate a notification the thread hides, like a call in the meeting view.
    patch(Message.prototype, {
        get notificationHidden() {
            return this.message_type === "notification" || super.notificationHidden;
        },
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Message:has(:text('message 101')):count(1)");
    await isInViewportOf(".o-mail-Message:has(:text('message 101'))", ".o-mail-Thread");
});

test("display day separator before first message of the day", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    pyEnv["mail.message"].create([
        {
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
        },
        {
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
        },
    ]);
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-DateSection:count(1)");
});

test("date section follows the day change", async () => {
    mockDate("2023-01-03 23:59:00", 0);
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    pyEnv["mail.message"].create({
        body: "not empty",
        date: "2023-01-03 12:00:00",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-DateSection:text('Today'):count(1)");
    await advanceTime(2 * 60 * 1000); // past midnight
    await waitFor(".o-mail-DateSection:text('Jan 3, 2023'):count(1)");
});

test("scroll position is kept when navigating from one channel to another [CAN FAIL DUE TO WINDOW SIZE]", async () => {
    mockDate("2023-01-03 12:00:00");
    const pyEnv = await startServer();
    const channelId_1 = pyEnv["discuss.channel"].create({
        name: "channel-1",
        channel_type: "channel",
        channel_member_ids: [
            Command.create({
                partner_id: serverState.partnerId,
                last_interest_dt: "2021-01-03 10:00:00",
            }),
        ],
    });
    const channelId_2 = pyEnv["discuss.channel"].create({
        name: "channel-2",
        channel_type: "channel",
        channel_member_ids: [
            Command.create({
                partner_id: serverState.partnerId,
                last_interest_dt: "2021-01-03 10:00:00",
            }),
        ],
    });
    // Fill both channels with random messages in order for the scrollbar to
    // appear.
    pyEnv["mail.message"].create(
        range(50).map((index) => ({
            body: "Non Empty Body ".repeat(25),
            message_type: "comment",
            model: "discuss.channel",
            res_id: index < 20 ? channelId_1 : channelId_2,
        }))
    );
    await start();
    await openDiscuss(channelId_1);
    await waitFor(".o-mail-Message:count(20)");
    const scrollValue1 = queryFirst(".o-mail-Thread").scrollHeight / 2;
    const scrollTopValue = queryFirst(".o-mail-Thread").scrollTop;
    await contains(".o-mail-Thread", { scroll: scrollTopValue });
    await tick(); // wait for the scroll to first unread to complete
    await scroll(".o-mail-Thread", scrollValue1);
    await click(".o-mail-NotificationItem:has(:text('channel-2'))");
    await waitFor(".o-mail-Message:count(30)");
    const scrollValue2 = queryFirst(".o-mail-Thread").scrollHeight / 3;
    await contains(".o-mail-Thread", { scroll: scrollTopValue });
    await tick(); // wait for the scroll to first unread to complete
    await scroll(".o-mail-Thread", scrollValue2);
    await click(".o-mail-NotificationItem:has(:text('channel-1'))");
    await waitFor(".o-mail-Message:count(20)");
    await contains(".o-mail-Thread", { scroll: scrollValue1 });
    await click(".o-mail-NotificationItem:has(:text('channel-2'))");
    await waitFor(".o-mail-Message:count(30)");
    await contains(".o-mail-Thread", { scroll: scrollValue2 });
});

test("thread is still scrolling after scrolling up then to bottom", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "channel-1" });
    pyEnv["mail.message"].create(
        range(20).map(() => ({
            body: "Non Empty Body ".repeat(25),
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        }))
    );
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Message:count(20)");
    await waitFor(".o-mail-Thread:count(1)");
    await tick(); // wait for the scroll to first unread to complete
    await scroll(".o-mail-Thread", queryFirst(".o-mail-Thread").scrollHeight / 2);
    await scroll(".o-mail-Thread", "bottom");
    await insertText(".o-mail-Composer-input", "123");
    await press("Enter");
    await waitFor(".o-mail-Message:count(21)");
    await contains(".o-mail-Thread", { scroll: "bottom" });
});

test("should scroll to bottom on receiving new message if the list is initially scrolled to bottom (asc order)", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Foreigner partner" });
    const userId = pyEnv["res.users"].create({ name: "Foreigner user", partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    for (let i = 0; i <= 10; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await click(".o-mail-NotificationItem");
    await waitFor(".o-mail-Message:count(11)");
    await tick(); // wait for the scroll to first unread to complete
    await scroll(".o-mail-Thread", "bottom");
    await contains(".o-mail-Thread", { scroll: "bottom" });
    // simulate receiving a message
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "hello", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await waitFor(".o-mail-Message:count(12)");
    await contains(".o-mail-Thread", { scroll: "bottom" });
    // simulate receiving a very long message
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "hello".repeat(10000), message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await waitFor(".o-mail-Message:count(13)");
    await tick(); // wait for the scroll to first unread to complete
    // simulate receiving another short message
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "end-msg", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await waitFor(".o-mail-Message:count(14)");
    await tick(); // wait in case of an auto-scroll to happen
    const scrollTop = queryFirst(".o-mail-Thread").scrollTop; // around 590px with chat window sizing
    const scrollHeight = queryFirst(".o-mail-Thread").scrollHeight; // around 20000px with chat window sizing
    const clientHeight = queryFirst(".o-mail-Thread").clientHeight; // around 540px with chat window sizing
    expect(scrollHeight / 4).toBeGreaterThan(scrollTop + clientHeight); // viewport is still at least in the 1st quarter, meaning no scroll to bottom
});

test("should scroll to top of new very long message rendered after the scroll is applied (asc order)", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Foreigner partner" });
    const userId = pyEnv["res.users"].create({ name: "Foreigner user", partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    for (let i = 0; i <= 10; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    patch(UseForwardRefsToParent.prototype, {
        async registerRef(...args) {
            // Simulate a resize applying the scroll before the new message is rendered.
            await Promise.resolve();
            return super.registerRef(...args);
        },
    });
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await click(".o-mail-NotificationItem");
    await waitFor(".o-mail-Message:count(11)");
    await tick(); // wait for the scroll to first unread to complete
    await scroll(".o-mail-Thread", "bottom");
    await contains(".o-mail-Thread", { scroll: "bottom" });
    // simulate receiving a very long message
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "hello".repeat(10000), message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await waitFor(".o-mail-Message:count(12)");
    await tick(); // wait for the new message element to be registered
    // simulate receiving another short message
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "end-msg", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await waitFor(".o-mail-Message:count(13)");
    await tick(); // wait in case of an auto-scroll to happen
    const scrollTop = queryFirst(".o-mail-Thread").scrollTop;
    const scrollHeight = queryFirst(".o-mail-Thread").scrollHeight;
    const clientHeight = queryFirst(".o-mail-Thread").clientHeight;
    expect(scrollHeight / 4).toBeGreaterThan(scrollTop + clientHeight); // viewport is still at least in the 1st quarter, meaning no scroll to bottom
});

test("should not scroll on receiving new message if the list is initially scrolled anywhere else than bottom (asc order)", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Foreigner partner" });
    const userId = pyEnv["res.users"].create({ name: "Foreigner user", partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    for (let i = 0; i <= 20; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await click(".o-mail-NotificationItem");
    await waitFor(".o-mail-Message:count(21)");
    await contains(".o-mail-Thread", { scroll: 0 });
    // simulate receiving a message
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "hello", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await waitFor(".o-mail-Message:count(22)");
    await contains(".o-mail-ChatWindow .o-mail-Thread", { scroll: 0 });
});

test("Mention a partner with special character (e.g. apostrophe ')", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "usatyi@example.com",
        name: "Pynya's spokesman",
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "@");
    await insertText(".o-mail-Composer-input", "Pyn");
    await click('.o-mail-Composer-suggestion:has(:text("Pynya\'s spokesman"))');
    await contains(".o-mail-Composer-input", { value: "@Pynya's spokesman " });
    await press("Enter");
    await waitFor(
        `.o-mail-Message-body .o_mail_redirect[data-oe-id="${partnerId}"][data-oe-model="res.partner"]:text("@Pynya's spokesman"):count(1)`
    );
});

test("mention 2 different partners that have the same name", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        {
            email: "partner1@example.com",
            name: "TestPartner",
        },
        {
            email: "partner2@example.com",
            name: "TestPartner",
        },
    ]);
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId_1 }),
            Command.create({ partner_id: partnerId_2 }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "@Te");
    await click(":nth-child(1 of .o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "@TestPartner " });
    await insertText(".o-mail-Composer-input", "@Te");
    await click(":nth-child(2 of .o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "@TestPartner @TestPartner " });
    await press("Enter");
    await waitFor(
        `.o-mail-Message-body .o_mail_redirect[data-oe-id="${partnerId_1}"][data-oe-model="res.partner"]:text("@TestPartner"):count(1)`
    );
    await waitFor(
        `.o-mail-Message-body .o_mail_redirect[data-oe-id="${partnerId_2}"][data-oe-model="res.partner"]:text("@TestPartner"):count(1)`
    );
});

test("Post a message containing an email address followed by a mention on another line", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "email@odoo.com\n@Te");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "email@odoo.com\n@TestPartner " });
    await press("Enter");
    await waitFor(
        `.o-mail-Message-body .o_mail_redirect[data-oe-id="${partnerId}"][data-oe-model="res.partner"]:text("@TestPartner"):count(1)`
    );
});

test("basic rendering of canceled notification", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    const partnerId = pyEnv["res.partner"].create({ name: "Someone", email: "test@test.be" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "email",
        model: "discuss.channel",
        res_id: channelId,
    });
    pyEnv["mail.notification"].create({
        failure_type: "mail_smtp",
        mail_message_id: messageId,
        notification_status: "canceled",
        notification_type: "email",
        res_partner_id: partnerId,
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Message-notification [data-icon='mail']:count(1)");
    await click(".o-mail-Message-notification");
    await waitFor(".o-mail-MessageNotificationPopover:count(1)");
    await waitFor(".o-mail-MessageNotificationPopover [data-icon='delete']:count(1)");
    await waitFor(".o-mail-MessageNotificationPopover:text('ToSomeone(test@test.be)'):count(1)");
});

test("first unseen message should be directly preceded by the new message separator if there is a transient message just before it while composer is not focused", async () => {
    // The goal of removing the focus is to ensure the thread is not marked as seen automatically.
    // Indeed that would trigger set_last_seen_message no matter what, which is already covered by other tests.
    // The goal of this test is to cover the conditions specific to transient messages,
    // and the conditions from focus would otherwise shadow them.
    const pyEnv = await startServer();
    // Needed partner & user to allow simulation of message reception
    const partnerId = pyEnv["res.partner"].create({ name: "Foreigner partner" });
    const userId = pyEnv["res.users"].create({
        name: "Foreigner user",
        partner_id: partnerId,
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
        channel_member_ids: [
            Command.create({ partner_id: partnerId }),
            Command.create({ partner_id: serverState.partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "not empty");
    await press("Enter");
    await waitFor(".o-mail-Message:has(:text('not empty')):count(1)");
    // send a command that leads to receiving a transient message
    await insertText(".o-mail-Composer-input", "/who");
    await click(".o-mail-Composer button[title='Send']:enabled");
    await waitFor(".o-mail-Message:count(2)");
    // composer is focused by default, we remove that focus
    queryFirst(".o-mail-Composer-input").blur();
    // simulate receiving a message
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "test", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await waitFor(".o-mail-Message:count(3)");
    await waitFor(".o-mail-Thread-newMessage:contains('New'):count(1)");
    await waitFor(".o-mail-Message[aria-label='Note'] + .o-mail-Thread-newMessage:count(1)");
});

test.tags("focus required");
test("composer should be focused automatically after clicking on the send button", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Dummy Message");
    await press("Enter");
    await waitFor(".o-mail-Composer-input:focus:count(1)");
});

test("chat window header should not have unread counter for non-channel thread", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
    const partnerId = pyEnv["res.partner"].create({ name: "test" });
    const messageId = pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "not empty",
        model: "res.partner",
        needaction: true,
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.NOTIFICATION);
    await click(".o-mail-NotificationItem");
    await waitForNone(".o-mail-ChatWindow-counter:text('1')");
});

test("Thread messages are only loaded once", async () => {
    const pyEnv = await startServer();
    const channelIds = pyEnv["discuss.channel"].create([{ name: "General" }, { name: "Sales" }]);
    listenStoreFetch("/discuss/channel/messages", { logParams: ["/discuss/channel/messages"] });
    await start();
    pyEnv["mail.message"].create([
        {
            model: "discuss.channel",
            res_id: channelIds[0],
            body: "Message on channel1",
        },
        {
            model: "discuss.channel",
            res_id: channelIds[1],
            body: "Message on channel2",
        },
    ]);
    await openDiscuss(MENU_ACTIVE_IDS.CHANNEL);
    await click("button:has(:text('General'))");
    await waitStoreFetch([
        [
            "/discuss/channel/messages",
            { channel_id: channelIds[0], fetch_params: { limit: 60, around: 0 } },
        ],
    ]);
    await waitFor(".o-mail-Message-content:text('Message on channel1'):count(1)");
    await click("button:has(:text('Sales'))");
    await waitStoreFetch([
        [
            "/discuss/channel/messages",
            { channel_id: channelIds[1], fetch_params: { limit: 60, around: 0 } },
        ],
    ]);
    await waitFor(".o-mail-Message-content:text('Message on channel2'):count(1)");
    await click("button:has(:text('General'))");
    await waitStoreFetch();
    await waitFor(".o-mail-Message-content:text('Message on channel1'):count(1)");
});

test.tags("focus required");
test("[text composer] Opening thread with needaction messages should mark all messages of thread as read", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
    const [channelId, salesId] = pyEnv["discuss.channel"].create([
        { name: "General" },
        { name: "Sales" },
    ]);
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["mail.message"].create([
        { body: "Hello", model: "discuss.channel", res_id: channelId },
        { body: "World", model: "discuss.channel", res_id: channelId },
    ]);
    onRpc("mail.message", "mark_all_as_read", ({ args }) => {
        expect.step("mark-all-messages-as-read");
        expect(args[0]).toEqual([
            ["model", "=", "discuss.channel"],
            ["res_id", "=", channelId],
        ]);
    });
    listenStoreFetch("/discuss/channel/messages", { logParams: ["/discuss/channel/messages"] });
    await start();
    await openDiscuss(channelId);
    await expect.waitForSteps([
        `store fetch: /discuss/channel/messages - {"channel_id":${channelId},"fetch_params":{"limit":60,"around":0}}`,
    ]);
    await waitFor(".o-mail-Message:count(2)");
    await click("button:has(:text('Sales'))");
    await expect.waitForSteps([
        `store fetch: /discuss/channel/messages - {"channel_id":${salesId},"fetch_params":{"limit":60,"around":0}}`,
    ]);
    const messageId = pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "@Mitchell Admin",
        needaction: true,
        model: "discuss.channel",
        res_id: channelId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    // simulate receiving a new needaction message
    const [partner] = pyEnv["res.partner"].read(serverState.partnerId);
    pyEnv["bus.bus"]._sendone(partner, "mail.message/notification", {
        message_id: messageId,
        store_data: new Store()
            .add(pyEnv["mail.message"].browse(messageId), "_store_message_fields", {
                fields_params: { inbox_fields: true },
            })
            .as_dict(),
    });
    await click("button:has(:text('General')):has(.badge:text(1))");
    await expect.waitForSteps(["mark-all-messages-as-read"]);
});

test.tags("focus required", "html composer");
test("Opening thread with needaction messages should mark all messages of thread as read", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
    const [channelId, salesId] = pyEnv["discuss.channel"].create([
        { name: "General" },
        { name: "Sales" },
    ]);
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["mail.message"].create([
        { body: "Hello", model: "discuss.channel", res_id: channelId },
        { body: "World", model: "discuss.channel", res_id: channelId },
    ]);
    onRpc("mail.message", "mark_all_as_read", ({ args }) => {
        expect.step("mark-all-messages-as-read");
        expect(args[0]).toEqual([
            ["model", "=", "discuss.channel"],
            ["res_id", "=", channelId],
        ]);
    });
    listenStoreFetch("/discuss/channel/messages", { logParams: ["/discuss/channel/messages"] });
    await start();
    const composerService = getService("mail.composer");
    composerService.setHtmlComposer();
    await openDiscuss(channelId);
    await expect.waitForSteps([
        `store fetch: /discuss/channel/messages - {"channel_id":${channelId},"fetch_params":{"limit":60,"around":0}}`,
    ]);
    await waitFor(".o-mail-Message:count(2)");
    await click("button:has(:text('Sales'))");
    await expect.waitForSteps([
        `store fetch: /discuss/channel/messages - {"channel_id":${salesId},"fetch_params":{"limit":60,"around":0}}`,
    ]);
    const messageId = pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "@Mitchell Admin",
        needaction: true,
        model: "discuss.channel",
        res_id: channelId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    const [partner] = pyEnv["res.partner"].read(serverState.partnerId);
    pyEnv["bus.bus"]._sendone(partner, "mail.message/notification", {
        message_id: messageId,
        store_data: new Store()
            .add(pyEnv["mail.message"].browse(messageId), "_store_message_fields", {
                fields_params: { inbox_fields: true },
            })
            .as_dict(),
    });
    await click("button:has(:text('General')):has(.badge:text(1))");
    await expect.waitForSteps(["mark-all-messages-as-read"]);
});

test("[technical] Opening thread without needaction messages should not mark all messages of thread as read", async () => {
    const pyEnv = await startServer();
    const [channelId, salesChannelId] = pyEnv["discuss.channel"].create([
        { name: "General" },
        { name: "Sales" },
    ]);
    pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: channelId,
    });
    onRpc("mail.message", "mark_all_as_read", () => expect.step("mark-all-messages-as-read"));
    await start();
    await openDiscuss(salesChannelId);
    await click("button:has(:text('General'))");
    await waitFor(".o-mail-Message:count(1)");
    await tick();
    await expect.waitForSteps([]);
});

test.tags("focus required");
test("can be marked as read while loading", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ message_unread_counter: 1, partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    const loadDeferred = Promise.withResolvers();
    listenStoreFetch("/discuss/channel/messages", {
        async onRpc() {
            await loadDeferred.promise;
        },
    });
    await start();
    await openDiscuss();
    await waitFor(".o-mail-NotificationItem .o-discuss-badge:text('1'):count(1)");
    await click(".o-mail-NotificationItem:has(:text('Demo'))");
    loadDeferred.resolve();
    await waitStoreFetch("/discuss/channel/messages");
    await waitForNone(".o-discuss-badge");
});

test("message received while loading thread is kept in the thread", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        name: "General",
    });
    const { promise: loadPromise, resolve: loadResolve } = Promise.withResolvers();
    // Simulate an answer computed before Demo posts: a delayed mock route could include the post.
    listenStoreFetch("/discuss/channel/messages", {
        async onRpc(request) {
            const res = await mail_store.bind(MockServer.current)(request);
            expect.step("messages computed");
            await loadPromise;
            return res;
        },
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Thread-empty:count(1)");
    await expect.waitForSteps(["messages computed"]);
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Hello", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    // The message list is not rendered while the thread loads, so the empty
    // state going away is the only sign that the message reached the thread.
    await waitForNone(".o-mail-Thread-empty");
    loadResolve();
    await waitStoreFetch("/discuss/channel/messages");
    await waitFor(".o-mail-Message-content:has(:text('Hello')):count(1)");
});

test("message received while loading thread on last read message is shown once after scrolling down", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        name: "General",
    });
    const messageIds = pyEnv["mail.message"].create(
        Array.from({ length: 55 }, (_, i) => ({
            author_id: partnerId,
            body: `msg${i}`,
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        }))
    );
    const [selfMemberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", serverState.partnerId],
    ]);
    pyEnv["discuss.channel.member"].write([selfMemberId], {
        new_message_separator: messageIds[9],
    });
    const { promise: loadPromise, resolve: loadResolve } = Promise.withResolvers();
    // Simulate the answer reaching the client after Demo posts.
    listenStoreFetch("/discuss/channel/messages", {
        async onRpc(request) {
            const res = await mail_store.bind(MockServer.current)(request);
            await loadPromise;
            return res;
        },
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Thread-empty:count(1)");
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Hello", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await waitForNone(".o-mail-Thread-empty"); // wait for the message
    loadResolve();
    await waitStoreFetch("/discuss/channel/messages");
    await waitFor(".o-mail-Message-content:has(:text('msg39')):count(1)");
    await waitForNone(".o-mail-Message-content:has(:text('Hello'))");
    await scroll(".o-mail-Thread", "bottom");
    await waitStoreFetch("/discuss/channel/messages");
    await waitFor(".o-mail-Message-content:has(:text('msg54')):count(1)");
    await waitFor(".o-mail-Message-content:has(:text('Hello')):count(1)");
});

test("New message separator not appearing after showing composer on thread", async () => {
    const pyEnv = await startServer();
    pyEnv["mail.message"].create([
        {
            model: "res.partner",
            res_id: serverState.partnerId,
            body: "Message on partner",
        },
        {
            model: "res.partner",
            res_id: serverState.partnerId,
            body: "Message on partner",
        },
    ]);
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await waitFor("button:text('Log note'):count(1)");
    await waitForNone(".o-mail-Thread-newMessage");
    await click("button:text('Log note')");
    await waitForNone(".o-mail-Thread-newMessage");
});

test("Transient messages are added at the end of the thread", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Dummy Message");
    await press("Enter");
    await waitFor(".o-mail-Message:count(1)");
    await insertText(".o-mail-Composer-input", "/help");
    await click(".o-mail-Composer button[title='Send']:enabled");
    await waitFor(".o-mail-Message:count(2)");
    await waitFor(".o-mail-Message:eq(0):has(:text('Mitchell Admin')):count(1)");
    await waitFor(".o-mail-Message:eq(1):has(:text('OdooBot')):count(1)");
});

test("Can scroll to notification", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "notification 0",
        message_type: "notification",
        model: "discuss.channel",
        pinned_at: "2024-03-24 15:00:00",
        res_id: channelId,
    });
    let lastMessageId;
    for (let i = 0; i < 60; ++i) {
        lastMessageId = pyEnv["mail.message"].create({
            author_id: serverState.partnerId,
            body: `message ${i}`,
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    const [selfMemberId] = pyEnv["discuss.channel.member"].search([
        ["partner_id", "=", serverState.partnerId],
        ["channel_id", "=", channelId],
    ]);
    pyEnv["discuss.channel.member"].write([selfMemberId], {
        new_message_separator: lastMessageId + 1,
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Message:count(30)");
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await isInViewportOf(".o-mail-Message:contains(message 59)", ".o-mail-Thread");
    await click("[title='Pinned Messages']");
    await click(".o-discuss-PinnedMessagesPanel a[role='button']:text('Jump')");
    await isInViewportOf(".o-mail-NotificationMessage:contains(notification 0)", ".o-mail-Thread");
});

test("Update unread counter when receiving new message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const userId = pyEnv["res.users"].create({ name: "Demo User", partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                message_unread_counter: 1,
                partner_id: serverState.partnerId,
            }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(undefined);
    await waitFor(
        ".o-mail-NotificationItem:has(:text('Demo')) .o-discuss-badge:text('1'):count(1)"
    );

    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "Message 1",
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await waitFor(
        ".o-mail-NotificationItem:has(:text('Demo')) .o-discuss-badge:text('2'):count(1)"
    );
});

test("Show start message of conversation", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["discuss.channel"].create([
        { name: "ThreadOne", parent_channel_id: channelId, channel_type: "channel" },
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: partnerId }),
            ],
            channel_type: "group",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: partnerId }),
            ],
            channel_type: "chat",
        },
    ]);
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Thread:has(:text('Welcome to #General!')):count(1)");
    await waitFor(
        ".o-mail-Thread:has(:text('This is the start of the #General channel')):count(1)"
    );
    await click(".o-mail-NotificationItem:has(:text('ThreadOne'))");
    await waitFor(".o-mail-Thread:has(:text('ThreadOne')):count(1)");
    await waitFor(".o-mail-Thread:has(:text('Started by Mitchell Admin')):count(1)");
    await click(".o-mail-MessagingMenu-tab[data-id='chat']");
    await click(".o-mail-NotificationItem:has(:text('Demo'))");
    await waitFor(".o-mail-Thread:has(:text('Demo')):count(1)");
    await waitFor(
        ".o-mail-Thread:has(:text('This is the start of your direct chat with Demo')):count(1)"
    );
    await click(".o-mail-NotificationItem:has(:text('Mitchell Admin and Demo'))");
    await waitFor(".o-mail-Thread:has(:text('Mitchell Admin and Demo')):count(1)");
    await waitFor(
        ".o-mail-Thread:has(:text('This is the start of Mitchell Admin and Demo group')):count(1)"
    );
});
