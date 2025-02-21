import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, Deferred, press, tick } from "@odoo/hoot-dom";
import {
    asyncStep,
    patchWithCleanup,
    serverState,
    waitForSteps,
} from "@web/../tests/web_test_helpers";

import {
    SIZES,
    click,
    contains,
    defineMailModels,
    insertText,
    isInViewportOf,
    onRpcBefore,
    openDiscuss,
    openFormView,
    patchUiSize,
    scroll,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { PRESENT_VIEWPORT_THRESHOLD } from "@mail/core/common/thread";

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
    await contains(":nth-child(1 of .o-mail-Message)", { text: "Hello world!" });
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
    onRpcBefore("/discuss/channel/messages", tick); // small delay
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 30 });
    await click(".o-mail-MessageInReply .cursor-pointer");
    await click("[title='Jump to Present']");
    await contains("[title='Jump to Present']", { count: 0 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
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
    await contains(".o-mail-Message-content", {
        text: "Newly posted",
        after: [".o-mail-Message-content", { text: "Most Recent!" }], // should load around present
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
    let slowMessageFetchDeferred;
    onRpcBefore("/discuss/channel/messages", async () => {
        asyncStep("/discuss/channel/messages");
        await slowMessageFetchDeferred;
    });
    await start();
    await openDiscuss(channelId);
    await waitForSteps(["/discuss/channel/messages"]);
    await click("[title='Pinned Messages']");
    await click(".o-discuss-PinnedMessagesPanel a[role='button']", { text: "Jump" });
    await contains(".o-mail-Thread .o-mail-Message", { text: "first-message" });
    await animationFrame();
    slowMessageFetchDeferred = new Deferred();
    await click("[title='Jump to Present']");
    await animationFrame();
    await waitForSteps(["/discuss/channel/messages"]);
    await contains(".o-mail-Thread .o-mail-Message", { text: "first-message" });
    slowMessageFetchDeferred.resolve();
    await contains(".o-mail-Thread .o-mail-Message", { text: "first-message", count: 0 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
});
