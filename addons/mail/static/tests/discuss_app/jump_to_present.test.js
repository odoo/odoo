import {
    SIZES,
    click,
    contains,
    defineMailModels,
    insertText,
    onRpcBefore,
    openDiscuss,
    openFormView,
    patchUiSize,
    scroll,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";

import { PRESENT_VIEWPORT_THRESHOLD } from "@mail/core/common/thread";
import { serverState } from "@web/../tests/web_test_helpers";
import { queryFirst } from "@odoo/hoot-dom";

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

test("Basic jump to present when scrolling to outdated messages (chatter, DESC)", async () => {
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
    await click("[title='Jump to Present']");
    await contains("[title='Jump to Present']", { count: 0 });
    await contains(".o-mail-Chatter", { scroll: 0 });
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
    onRpcBefore("/discuss/channel/messages", async () => await new Promise(setTimeout)); // small delay
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
    await click(".o-mail-Composer button[aria-label='Send']:enabled");
    await contains("[title='Jump to Present']", { count: 0 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await contains(".o-mail-Message-content", {
        text: "Newly posted",
        after: [".o-mail-Message-content", { text: "Most Recent!" }], // should load around present
    });
});

test("show jump to present banner after scrolling up 10 messages", async () => {
    // when messages are short, 3 x PRESENT_VIEWPORT_THRESHOLD is used, otherwise
    // this is 10 x PRESENT_MESSAGE_THRESHOLD
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
    });
    for (let i = 0; i < 100; i++) {
        pyEnv["mail.message"].create({
            body: "<p>Non Empty Body</p>".repeat(100),
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    const newestMessageId = pyEnv["mail.message"].create({
        body: "<p>Newest</p>",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
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
    // make a notification in thread, just to make things complicated
    // pinning a message adds such notification
    await click(".o-mail-Message:contains(Newest) [title='Expand']");
    await click(".dropdown-item", { text: "Pin" });
    await click(".modal-footer button", { text: "Yeah, pin it!" });
    const top1 = queryFirst(".o-mail-Message").getBoundingClientRect().top;
    const top2 = queryFirst(".o-mail-Message:eq(1)").getBoundingClientRect().top;
    const messageHeight = top2 - top1;
    // scroll slightly (1 long message)
    await scroll(".o-mail-Thread", queryFirst(".o-mail-Thread").scrollTop - messageHeight);
    await contains("[title='Jump to Present']", { count: 0 });
    // scroll to 5th message before newest
    await scroll(".o-mail-Thread", queryFirst(".o-mail-Thread").scrollTop - 4 * messageHeight);
    await contains("[title='Jump to Present']", { count: 0 });
    // scroll to around 10th message before newest
    await scroll(".o-mail-Thread", queryFirst(".o-mail-Thread").scrollTop - 5 * messageHeight);
    await contains("[title='Jump to Present']");
});
