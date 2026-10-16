import { after, describe, expect, test } from "@odoo/hoot";
import { animationFrame, Deferred, delay, press, queryFirst, tick } from "@odoo/hoot-dom";
import { Command, patchWithCleanup, serverState, withUser } from "@web/../tests/web_test_helpers";

import {
    SIZES,
    click,
    contains,
    defineMailModels,
    insertText,
    isInViewportOf,
    listenStoreFetch,
    openDiscuss,
    openFormView,
    patchUiSize,
    scroll,
    start,
    startServer,
    waitStoreFetch,
} from "@mail/../tests/mail_test_helpers";
import { PRESENT_VIEWPORT_THRESHOLD } from "@mail/core/common/thread";
import { rpc } from "@web/core/network/rpc";

describe.current.tags("desktop");
defineMailModels();

test("Basic jump to present when scrolling to outdated messages", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    for (let i = 0; i < 20; i++) {
        pyEnv["mail.message"].create({
            body: "Non Empty Body ".repeat(100),
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 20 });
    await contains(".o-mail-Thread");
    expect(document.querySelector(".o-mail-Thread").scrollHeight).toBeGreaterThan(
        PRESENT_VIEWPORT_THRESHOLD * document.querySelector(".o-mail-Thread").clientHeight,
        { message: "should have enough scroll height to trigger jump to present" }
    );
    await click("[title='Jump to Present']");
    await contains("[title='Jump to Present']", { count: 0 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
});

test("Jump to present reaches the bottom in a browser without scrollend", async () => {
    // Simulate a browser without the "scrollend" event.
    const onscrollend = Object.getOwnPropertyDescriptor(window, "onscrollend");
    delete window.onscrollend;
    after(() => Object.defineProperty(window, "onscrollend", onscrollend));
    // Simulate a smooth scroll that stalls halfway.
    patchWithCleanup(Element.prototype, {
        scrollTo(...args) {
            if (args[0]?.behavior === "smooth") {
                super.scrollTo({ top: args[0].top / 2 });
                setTimeout(() => super.scrollTo(...args), 1200);
                return;
            }
            return super.scrollTo(...args);
        },
    });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    for (let i = 0; i < 20; i++) {
        pyEnv["mail.message"].create({
            body: "Non Empty Body ".repeat(100),
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 20 });
    await click("[title='Jump to Present']");
    await contains(".o-mail-Thread", {
        contains: [".o-mail-Message", { count: 20 }],
        scroll: "bottom",
    });
});

test("Jump to a pinned message during jump to present in a browser without scrollend", async () => {
    // Simulate a browser without the "scrollend" event.
    const onscrollend = Object.getOwnPropertyDescriptor(window, "onscrollend");
    delete window.onscrollend;
    after(() => Object.defineProperty(window, "onscrollend", onscrollend));
    // Simulate a smooth scroll that stalls at its start.
    const smoothScrollStarted = new Deferred();
    patchWithCleanup(Element.prototype, {
        scrollIntoView(...args) {
            if (args[0]?.behavior === "smooth") {
                return super.scrollIntoView({ ...args[0], behavior: "instant" });
            }
            return super.scrollIntoView(...args);
        },
        scrollTo(...args) {
            if (args[0]?.behavior === "smooth") {
                smoothScrollStarted.resolve();
                return;
            }
            return super.scrollTo(...args);
        },
    });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    for (let i = 0; i < 20; i++) {
        pyEnv["mail.message"].create({
            body: i === 14 ? "pinned-message" : "Non Empty Body ".repeat(100),
            message_type: "comment",
            model: "discuss.channel",
            pinned_at: i === 14 ? "2020-02-12 08:30:00" : undefined,
            res_id: channelId,
        });
    }
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 20 });
    await click("[title='Pinned Messages']");
    await contains(".o-discuss-PinnedMessagesPanel a[role='button']:text(Jump):count(1)");
    await click("[title='Jump to Present']");
    await smoothScrollStarted;
    await click(".o-discuss-PinnedMessagesPanel a[role='button']:text(Jump)");
    await contains(".o-mail-Message.o-highlighted .o-mail-Message-body:text(pinned-message)");
    await contains(".o-mail-Message.o-highlighted", { count: 0 });
    await isInViewportOf(
        ".o-mail-Thread .o-mail-Message-body:text(pinned-message)",
        ".o-mail-Thread"
    );
    await contains(".o-mail-Thread", { count: 0, scroll: "bottom" });
});

test("Jump to present keeps the position of a user who scrolls up in a browser without scrollend", async () => {
    // Simulate a browser without the "scrollend" event.
    const onscrollend = Object.getOwnPropertyDescriptor(window, "onscrollend");
    delete window.onscrollend;
    after(() => Object.defineProperty(window, "onscrollend", onscrollend));
    // Simulate a smooth scroll that stalls halfway.
    const smoothScrollStarted = new Deferred();
    patchWithCleanup(Element.prototype, {
        scrollTo(...args) {
            if (args[0]?.behavior === "smooth") {
                super.scrollTo({ top: args[0].top / 2 });
                smoothScrollStarted.resolve();
                return;
            }
            return super.scrollTo(...args);
        },
    });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    for (let i = 0; i < 20; i++) {
        pyEnv["mail.message"].create({
            body: "Non Empty Body ".repeat(100),
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 20 });
    await click("[title='Jump to Present']");
    await smoothScrollStarted;
    await animationFrame();
    await animationFrame(); // wait for the scroll event of the stalled scroll
    const userScrollTop = queryFirst(".o-mail-Thread").scrollTop - 200;
    await scroll(".o-mail-Thread", userScrollTop);
    await delay(1000); // wait for the end of the smooth scroll check
    expect(Math.abs(queryFirst(".o-mail-Thread").scrollTop - userScrollTop)).toBeLessThan(2);
    await contains(".o-mail-Thread", { count: 0, scroll: "bottom" });
});

test("Jump to present reaches the bottom when a message arrives during the smooth scroll", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Bob" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        name: "General",
    });
    for (let i = 0; i < 20; i++) {
        pyEnv["mail.message"].create({
            body: "Non Empty Body ".repeat(100),
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 20 });
    const smoothScrollStarted = new Deferred();
    patchWithCleanup(Element.prototype, {
        scrollTo(...args) {
            if (args[0]?.behavior === "smooth") {
                this.addEventListener("scroll", () => smoothScrollStarted.resolve(), {
                    once: true,
                });
            }
            return super.scrollTo(...args);
        },
    });
    await click("[title='Jump to Present']");
    await smoothScrollStarted;
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "New message", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Thread", {
        contains: [".o-mail-Message", { count: 21 }],
        scroll: "bottom",
    });
});

test("Basic jump to present when scrolling to outdated messages (DESC, chatter aside)", async () => {
    patchUiSize({ size: SIZES.XXL });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo User" });
    for (let i = 0; i < 20; i++) {
        pyEnv["mail.message"].create({
            body: "Non Empty Body ".repeat(100),
            message_type: "comment",
            model: "res.partner",
            res_id: partnerId,
        });
    }
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Message", { count: 20 });
    await contains(".o-mail-Thread");
    expect(document.querySelector(".o-mail-Chatter").scrollHeight).toBeGreaterThan(
        PRESENT_VIEWPORT_THRESHOLD * document.querySelector(".o-mail-Chatter").clientHeight,
        { message: "should have enough scroll height to trigger jump to present" }
    );
    await contains(".o-mail-Chatter", { scroll: 0 });
    await scroll(".o-mail-Chatter", "bottom");
    await isInViewportOf("[title='Jump to Present']", ".o-mail-Thread");
    await click("[title='Jump to Present']");
    await contains("[title='Jump to Present']", { count: 0 });
    await contains(".o-mail-Chatter", { scroll: 0 });
});

test("Basic jump to present when scrolling to outdated messages (DESC, chatter non-aside)", async () => {
    patchUiSize({ size: SIZES.MD });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo User" });
    for (let i = 0; i < 20; i++) {
        pyEnv["mail.message"].create({
            body: "Non Empty Body ".repeat(100),
            message_type: "comment",
            model: "res.partner",
            res_id: partnerId,
        });
    }
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Message", { count: 20 });
    await contains(".o_content");
    expect(document.querySelector(".o_content").scrollHeight).toBeGreaterThan(
        PRESENT_VIEWPORT_THRESHOLD * document.querySelector(".o_content").clientHeight,
        { message: "should have enough scroll height to trigger jump to present" }
    );
    await contains(".o_content", { scroll: 0 });
    await scroll(".o_content", "bottom");
    await isInViewportOf("[title='Jump to Present']", ".o_content");
    await click("[title='Jump to Present']");
    await contains("[title='Jump to Present']", { count: 0 });
    await contains(".o_content", { scroll: 0 });
});

test("Jump to old reply should prompt jump to present", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const oldestMessageId = pyEnv["mail.message"].create({
        body: "<p>Hello world!</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    for (let i = 0; i < 100; i++) {
        pyEnv["mail.message"].create({
            body: "<p>Non Empty Body</p>".repeat(100),
            message_type: "comment",
            model: "discuss.channel",
            /**
             * The first message following the oldest message should have it as its parent message
             * so that the oldest message is inserted through the parent field during "load around"
             * to have the coverage of this part of the code (in particular having parent message
             * body being inserted with markup).
             */
            parent_id: i === 0 ? oldestMessageId : undefined,
            res_id: channelId,
        });
    }
    const newestMessageId = pyEnv["mail.message"].create({
        body: "Most Recent!",
        model: "discuss.channel",
        res_id: channelId,
        parent_id: oldestMessageId,
    });
    const [selfMember] = pyEnv["discuss.channel.member"].search_read([
        ["partner_id", "=", serverState.partnerId],
        ["channel_id", "=", channelId],
    ]);
    pyEnv["discuss.channel.member"].write([selfMember.id], {
        new_message_separator: newestMessageId + 1,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 30 });
    await click(".o-mail-MessageInReply .cursor-pointer");
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-Message:eq(0):has(:text('Hello world!'))");
    await click("[title='Jump to Present']");
    await contains("[title='Jump to Present']", { count: 0 });
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
});

test("Jump to old reply should prompt jump to present (RPC small delay)", async () => {
    // same test as before but with a small RPC delay
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const oldestMessageId = pyEnv["mail.message"].create({
        body: "<p>Hello world!</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    for (let i = 0; i < 100; i++) {
        pyEnv["mail.message"].create({
            body: "<p>Non Empty Body</p>".repeat(100),
            message_type: "comment",
            model: "discuss.channel",
            /**
             * The first message following the oldest message should have it as its parent message
             * so that the oldest message is inserted through the parent field during "load around"
             * to have the coverage of this part of the code (in particular having parent message
             * body being inserted with markup).
             */
            parent_id: i === 0 ? oldestMessageId : undefined,
            res_id: channelId,
        });
    }
    const newestMessageId = pyEnv["mail.message"].create({
        body: "Most Recent!",
        model: "discuss.channel",
        res_id: channelId,
        parent_id: oldestMessageId,
    });
    const [selfMember] = pyEnv["discuss.channel.member"].search_read([
        ["partner_id", "=", serverState.partnerId],
        ["channel_id", "=", channelId],
    ]);
    pyEnv["discuss.channel.member"].write([selfMember.id], {
        new_message_separator: newestMessageId + 1,
    });
    listenStoreFetch("/discuss/channel/messages", {
        logParams: ["/discuss/channel/messages"],
        async onRpc() {
            await tick();
        },
    });
    await start();
    await openDiscuss(channelId);
    await waitStoreFetch([
        [
            "/discuss/channel/messages",
            { channel_id: channelId, fetch_params: { limit: 60, around: 103 } },
        ],
    ]);
    await contains(".o-mail-Message", { count: 30 });
    await click(".o-mail-MessageInReply .cursor-pointer");
    await click("[title='Jump to Present']");
    await contains("[title='Jump to Present']", { count: 0 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await waitStoreFetch([
        [
            "/discuss/channel/messages",
            { channel_id: channelId, fetch_params: { limit: 60, around: 1 } },
        ],
        ["/discuss/channel/messages", { channel_id: channelId, fetch_params: { limit: 30 } }],
    ]);
});

test("Post message when seeing old message should jump to present", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const oldestMessageId = pyEnv["mail.message"].create({
        body: "<p>Hello world!</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    for (let i = 0; i < 100; i++) {
        pyEnv["mail.message"].create({
            body: "<p>Non Empty Body</p>".repeat(100),
            message_type: "comment",
            model: "discuss.channel",
            /**
             * The first message following the oldest message should have it as its parent message
             * so that the oldest message is inserted through the parent field during "load around"
             * to have the coverage of this part of the code (in particular having parent message
             * body being inserted with markup).
             */
            parent_id: i === 0 ? oldestMessageId : undefined,
            res_id: channelId,
        });
    }
    pyEnv["mail.message"].create({
        body: "Most Recent!",
        model: "discuss.channel",
        res_id: channelId,
        parent_id: oldestMessageId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 30 });
    await click(".o-mail-MessageInReply .cursor-pointer");
    await contains("[title='Jump to Present']");
    await insertText(".o-mail-Composer-input", "Newly posted");
    await press("Enter");
    await contains("[title='Jump to Present']", { count: 0 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await contains(".o-mail-Message-content:has(:text('Newly posted'))", {
        after: [".o-mail-Message-content:has(:text('Most Recent!'))"], // should load around present
    });
});

test("when triggering jump to present, keeps showing old messages until recent ones are loaded", async () => {
    // make scroll behavior instantaneous.
    patchWithCleanup(Element.prototype, {
        scrollIntoView() {
            return super.scrollIntoView(true);
        },
        scrollTo(...args) {
            if (typeof args[0] === "object" && args[0]?.behavior === "smooth") {
                return super.scrollTo({ ...args[0], behavior: "instant" });
            }
            return super.scrollTo(...args);
        },
    });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    for (let i = 0; i < 60; i++) {
        pyEnv["mail.message"].create({
            body: i === 0 ? "first-message" : "Non Empty Body ".repeat(100),
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
            pinned_at: i === 0 ? "2020-02-12 08:30:00" : undefined,
        });
    }
    let slowMessageFetchDeferred = Promise.withResolvers();
    slowMessageFetchDeferred.resolve();
    listenStoreFetch("/discuss/channel/messages", {
        async onRpc() {
            await slowMessageFetchDeferred.promise;
        },
    });
    await start();
    await openDiscuss(channelId);
    await waitStoreFetch("/discuss/channel/messages");
    await click("[title='Pinned Messages']");
    await click(".o-discuss-PinnedMessagesPanel a[role='button']:text('Jump')");
    await contains(".o-mail-Thread .o-mail-Message:has(:text('first-message'))");
    await animationFrame();
    slowMessageFetchDeferred = Promise.withResolvers();
    await click("[title='Jump to Present']");
    await animationFrame();
    await contains(".o-mail-Thread .o-mail-Message:has(:text('first-message'))");
    slowMessageFetchDeferred.resolve();
    await waitStoreFetch("/discuss/channel/messages");
    await contains(".o-mail-Thread .o-mail-Message:has(:text('first-message'))", { count: 0 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
});

test("focus composer after jump to present", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create(
        [...Array(40).keys()].map((i) => ({
            body: `<p>Non Empty Message ${i}</p>`,
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        }))
    );
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-Composer.o-focused");
    queryFirst(".o-mail-Composer-input").blur();
    await contains(".o-mail-Composer.o-focused", { count: 0 });
    await click("[title='Jump to Present']");
    await contains(".o-mail-Composer.o-focused");
});
