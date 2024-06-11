/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { PRESENT_THRESHOLD } from "@mail/core/common/thread";
import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains, insertText, scroll } from "@web/../tests/utils";
import { SIZES, patchUiSize } from "../helpers/patch_ui_size";

QUnit.module("jump to present");

QUnit.test("Basic jump to present when scrolling to outdated messages", async (assert) => {
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
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 20 });
    await contains(".o-mail-Thread");
    assert.ok(
        document.querySelector(".o-mail-Thread").scrollHeight > PRESENT_THRESHOLD,
        "should have enough scroll height to trigger jump to present"
    );
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await scroll(".o-mail-Thread", 0);
    await contains(".o-mail-Thread", { text: "You're viewing older messagesJump to Present" });
    await click(".o-mail-Thread-jumpPresent");
    await contains(".o-mail-Thread", {
        count: 0,
        text: "You're viewing older messagesJump to Present",
    });
    await contains(".o-mail-Thread", { scroll: "bottom" });
});

QUnit.test(
    "Basic jump to present when scrolling to outdated messages (chatter, DESC)",
    async (assert) => {
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
        const { openFormView } = await start();
        await openFormView("res.partner", partnerId);
        await contains(".o-mail-Message", { count: 20 });
        await contains(".o-mail-Thread");
        assert.ok(
            document.querySelector(".o-mail-Thread").scrollHeight > PRESENT_THRESHOLD,
            "should have enough scroll height to trigger jump to present"
        );
        await contains(".o-mail-Chatter", { scroll: 0 });
        await scroll(".o-mail-Chatter", "bottom");
        await contains(".o-mail-Chatter", { text: "You're viewing older messagesJump to Present" });
        await click(".o-mail-Thread-jumpPresent");
        await contains(".o-mail-Thread", {
            count: 0,
            text: "You're viewing older messagesJump to Present",
        });
        await contains(".o-mail-Chatter", { scroll: 0 });
    }
);

QUnit.test("Jump to old reply should prompt jump to present", async () => {
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
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 30 });
    await click(".o-mail-MessageInReply .cursor-pointer");
    await contains(".o-mail-Message", { count: 16 });
    await contains(":nth-child(1 of .o-mail-Message)", { text: "Hello world!" });
    await contains(".o-mail-Thread-jumpPresent");
    await click(".o-mail-Thread-jumpPresent");
    await contains(".o-mail-Thread-jumpPresent", { count: 0 });
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
});

QUnit.test("Jump to old reply should prompt jump to present (RPC small delay)", async () => {
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
    pyEnv["mail.message"].create({
        body: "Most Recent!",
        model: "discuss.channel",
        res_id: channelId,
        parent_id: oldestMessageId,
    });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/discuss/channel/messages") {
                await new Promise(setTimeout); // small delay
            }
        },
    });
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 30 });
    await click(".o-mail-MessageInReply .cursor-pointer");
    await contains(".o-mail-Thread-jumpPresent");
    await click(".o-mail-Thread-jumpPresent");
    await contains(".o-mail-Thread-jumpPresent", { count: 0 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
});

QUnit.test("Post message when seeing old message should jump to present", async () => {
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
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 30 });
    await click(".o-mail-MessageInReply .cursor-pointer");
    await contains(".o-mail-Thread-jumpPresent");
    await insertText(".o-mail-Composer-input", "Newly posted");
    await click(".o-mail-Composer button:enabled", { text: "Send" });
    await contains(".o-mail-Thread-jumpPresent", { count: 0 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await contains(".o-mail-Message-content", {
        text: "Newly posted",
        after: [".o-mail-Message-content", { text: "Most Recent!" }], // should load around present
    });
});
