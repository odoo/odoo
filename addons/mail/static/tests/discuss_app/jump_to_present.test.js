import { after, describe, expect, test } from "@odoo/hoot";
import { animationFrame, delay, press, tick, waitFor, waitForNone } from "@odoo/hoot-dom";
import { Command, contains, serverState, withUser } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";

import {
    actionPanel,
    SIZES,
    click,
    contains as mailContains,
    defineMailModels,
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
import { insertTextInComposer } from "@mail/../tests/mail_test_helpers_composer";
import { PRESENT_VIEWPORT_THRESHOLD, SMOOTH_SCROLLING_CHECK_DELAY } from "@mail/core/common/thread";
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
    await waitFor(".o-mail-Message:count(20)");
    await waitFor(".o-mail-Thread:count(1)");
    expect(document.querySelector(".o-mail-Thread").scrollHeight).toBeGreaterThan(
        PRESENT_VIEWPORT_THRESHOLD * document.querySelector(".o-mail-Thread").clientHeight,
        { message: "should have enough scroll height to trigger jump to present" }
    );
    await contains("[title='Jump to Present']:count(1)").click();
    await waitForNone("[title='Jump to Present']");
    await mailContains(".o-mail-Thread", { scroll: "bottom" });
});

test("Jump to present reaches the bottom in a browser without scrollend", async () => {
    // Simulate a browser without the "scrollend" event.
    const onscrollend = Object.getOwnPropertyDescriptor(window, "onscrollend");
    delete window.onscrollend;
    after(() => Object.defineProperty(window, "onscrollend", onscrollend));
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
    await waitFor(".o-mail-Message:count(20)");
    const smoothScrollStarted = Promise.withResolvers();
    patch(Element.prototype, {
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
    await smoothScrollStarted.promise;
    await delay(SMOOTH_SCROLLING_CHECK_DELAY + 50);
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "New message", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await mailContains(".o-mail-Thread", {
        contains: [".o-mail-Message", { count: 21 }],
        scroll: "bottom",
    });
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
    await waitFor(".o-mail-Message:count(20)");
    const smoothScrollStarted = Promise.withResolvers();
    patch(Element.prototype, {
        scrollTo(...args) {
            if (args[0]?.behavior === "smooth") {
                this.addEventListener("scroll", () => smoothScrollStarted.resolve(), {
                    once: true,
                });
            }
            return super.scrollTo(...args);
        },
    });
    await contains("[title='Jump to Present']:count(1)").click();
    await smoothScrollStarted.promise;
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "New message", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await mailContains(".o-mail-Thread", {
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
    await waitFor(".o-mail-Message:count(20)");
    await waitFor(".o-mail-Thread:count(1)");
    expect(document.querySelector(".o-mail-Chatter").scrollHeight).toBeGreaterThan(
        PRESENT_VIEWPORT_THRESHOLD * document.querySelector(".o-mail-Chatter").clientHeight,
        { message: "should have enough scroll height to trigger jump to present" }
    );
    await mailContains(".o-mail-Chatter", { scroll: 0 });
    await scroll(".o-mail-Chatter", "bottom");
    await isInViewportOf("[title='Jump to Present']", ".o-mail-Thread");
    await contains("[title='Jump to Present']:count(1)").click();
    await waitForNone("[title='Jump to Present']");
    await mailContains(".o-mail-Chatter", { scroll: 0 });
});

test.tags("owl3");
test.skip("Basic jump to present when scrolling to outdated messages (DESC, chatter non-aside)", async () => {
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
    await waitFor(".o-mail-Message:count(20)");
    await waitFor(".o_content:count(1)");
    expect(document.querySelector(".o_content").scrollHeight).toBeGreaterThan(
        PRESENT_VIEWPORT_THRESHOLD * document.querySelector(".o_content").clientHeight,
        { message: "should have enough scroll height to trigger jump to present" }
    );
    await mailContains(".o_content", { scroll: 0 });
    await scroll(".o_content", "bottom");
    await isInViewportOf("[title='Jump to Present']", ".o_content");
    await contains("[title='Jump to Present']:count(1)").click();
    await waitForNone("[title='Jump to Present']");
    await mailContains(".o_content", { scroll: 0 });
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
    await waitFor(".o-mail-Message:count(30)");
    await contains(".o-mail-MessageInReply .cursor-pointer:count(1)").click();
    await waitFor(".o-mail-Message:eq(0):has(:text('Hello world!')):count(1)");
    await waitFor(".o-mail-Message:count(31)");
    await contains("[title='Jump to Present']:count(1)").click();
    await waitForNone("[title='Jump to Present']");
    await waitFor(".o-mail-Message:count(30)");
    await mailContains(".o-mail-Thread", { scroll: "bottom" });
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
    await waitFor(".o-mail-Message:count(30)");
    await contains(".o-mail-MessageInReply .cursor-pointer:count(1)").click();
    await waitFor(".o-mail-Message:eq(0):has(:text('Hello world!')):count(1)");
    await waitFor(".o-mail-Message:count(31)");
    await contains("[title='Jump to Present']:count(1)").click();
    await waitForNone("[title='Jump to Present']");
    await mailContains(".o-mail-Thread", { scroll: "bottom" });
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
    await waitFor(".o-mail-Message:count(30)");
    await contains(".o-mail-MessageInReply .cursor-pointer:count(1)").click();
    await waitFor("[title='Jump to Present']:count(1)");
    await insertTextInComposer(".o-mail-Composer", "Newly posted");
    await press("Enter");
    await waitForNone("[title='Jump to Present']");
    await mailContains(".o-mail-Thread", { scroll: "bottom" });
    await mailContains(".o-mail-Message-content:has(:text('Newly posted'))", {
        after: [".o-mail-Message-content:has(:text('Most Recent!'))"], // should load around present
    });
});

test("when triggering jump to present, keeps showing old messages until recent ones are loaded", async () => {
    // make scroll behavior instantaneous.
    patch(Element.prototype, {
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
    await click(`${actionPanel("Pinned Messages")} a[role='button']:text('Jump')`);
    await waitFor(".o-mail-Thread .o-mail-Message:has(:text('first-message')):count(1)");
    await animationFrame();
    slowMessageFetchDeferred = Promise.withResolvers();
    await click("[title='Jump to Present']");
    await animationFrame();
    await waitFor(".o-mail-Thread .o-mail-Message:has(:text('first-message')):count(1)");
    slowMessageFetchDeferred.resolve();
    await waitStoreFetch("/discuss/channel/messages");
    await waitForNone(".o-mail-Thread .o-mail-Message:has(:text('first-message'))");
    await mailContains(".o-mail-Thread", { scroll: "bottom" });
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
    await waitFor(".o-mail-Message:count(30)");
    await waitFor(".o-mail-Composer.o-focused:count(1)");
    await contains(".o_navbar").click(); // click away
    await waitForNone(".o-mail-Composer.o-focused");
    await contains("[title='Jump to Present']:count(1)").click();
    await waitFor(".o-mail-Composer.o-focused:count(1)");
});

test("Jump to present when pressing hotkey ArrowUp", async () => {
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
    await waitFor(".o-mail-Message:count(20)");
    await waitFor(".o-mail-Thread");
    expect(document.querySelector(".o-mail-Chatter").scrollHeight).toBeGreaterThan(
        PRESENT_VIEWPORT_THRESHOLD * document.querySelector(".o-mail-Chatter").clientHeight,
        { message: "should have enough scroll height to trigger jump to present" }
    );
    await mailContains(".o-mail-Chatter", { scroll: 0 });
    await scroll(".o-mail-Chatter", "bottom");
    await isInViewportOf("[title='Jump to Present']", ".o-mail-Thread");
    await contains(".o-mail-Thread").focus();
    await press(["control", "ArrowUp"]);
    await mailContains(".o-mail-Chatter", { scroll: 0 });
});
