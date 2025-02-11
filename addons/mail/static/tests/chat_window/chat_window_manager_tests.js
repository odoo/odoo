/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import {
    CHAT_WINDOW_END_GAP_WIDTH,
    CHAT_WINDOW_INBETWEEN_WIDTH,
    CHAT_WINDOW_WIDTH,
} from "@mail/core/common/chat_window_service";
import { Command } from "@mail/../tests/helpers/command";
import { patchUiSize } from "@mail/../tests/helpers/patch_ui_size";
import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains } from "@web/../tests/utils";

QUnit.module("chat window manager");

QUnit.test("chat window does not fetch messages if hidden", async (assert) => {
    const pyEnv = await startServer();
    const [channeId1, channelId2, channelId3] = pyEnv["discuss.channel"].create([
        {
            channel_member_ids: [
                Command.create({ is_minimized: true, partner_id: pyEnv.currentPartnerId }),
            ],
        },
        {
            channel_member_ids: [
                Command.create({ is_minimized: true, partner_id: pyEnv.currentPartnerId }),
            ],
        },
        {
            channel_member_ids: [
                Command.create({ is_minimized: true, partner_id: pyEnv.currentPartnerId }),
            ],
        },
    ]);
    pyEnv["mail.message"].create([
        {
            body: "Orange",
            res_id: channeId1,
            message_type: "comment",
            model: "discuss.channel",
        },
        {
            body: "Apple",
            res_id: channelId2,
            message_type: "comment",
            model: "discuss.channel",
        },
        {
            body: "Banana",
            res_id: channelId3,
            message_type: "comment",
            model: "discuss.channel",
        },
    ]);
    patchUiSize({ width: 900 });
    assert.ok(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 2 + CHAT_WINDOW_INBETWEEN_WIDTH < 900
    );
    assert.ok(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 3 + CHAT_WINDOW_INBETWEEN_WIDTH * 2 >
            900
    );
    await start({
        mockRPC(route, args) {
            if (route === "/discuss/channel/messages") {
                assert.step("fetch_messages");
            }
        },
    });
    await contains(".o-mail-ChatWindow", { count: 2 });
    await contains(".o-mail-ChatWindowHiddenToggler");
    await contains(".o-mail-Message-content", { text: "Orange" });
    await contains(".o-mail-Message-content", { count: 0, text: "Apple" });
    await contains(".o-mail-Message-content", { text: "Banana" });
    assert.verifySteps(["fetch_messages", "fetch_messages"]);
});

QUnit.test("click on hidden chat window should fetch its messages", async (assert) => {
    const pyEnv = await startServer();
    const [channeId1, channelId2, channelId3] = pyEnv["discuss.channel"].create([
        {
            channel_member_ids: [
                Command.create({ is_minimized: true, partner_id: pyEnv.currentPartnerId }),
            ],
        },
        {
            channel_member_ids: [
                Command.create({ is_minimized: true, partner_id: pyEnv.currentPartnerId }),
            ],
        },
        {
            channel_member_ids: [
                Command.create({ is_minimized: true, partner_id: pyEnv.currentPartnerId }),
            ],
        },
    ]);
    pyEnv["mail.message"].create([
        {
            body: "Orange",
            res_id: channeId1,
            message_type: "comment",
            model: "discuss.channel",
        },
        {
            body: "Apple",
            res_id: channelId2,
            message_type: "comment",
            model: "discuss.channel",
        },
        {
            body: "Banana",
            res_id: channelId3,
            message_type: "comment",
            model: "discuss.channel",
        },
    ]);
    patchUiSize({ width: 900 });
    assert.ok(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 2 + CHAT_WINDOW_INBETWEEN_WIDTH < 900
    );
    assert.ok(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 3 + CHAT_WINDOW_INBETWEEN_WIDTH * 2 >
            900
    );
    await start({
        mockRPC(route, args) {
            if (route === "/discuss/channel/messages") {
                assert.step("fetch_messages");
            }
        },
    });
    await contains(".o-mail-ChatWindow", { count: 2 });
    await contains(".o-mail-ChatWindowHiddenToggler");
    await contains(".o-mail-Message-content", { text: "Orange" });
    await contains(".o-mail-Message-content", { count: 0, text: "Apple" });
    await contains(".o-mail-Message-content", { text: "Banana" });
    assert.verifySteps(["fetch_messages", "fetch_messages"]);
    await click(".o-mail-ChatWindowHiddenToggler");
    await click(".o-mail-ChatWindowHiddenMenu-item .o-mail-ChatWindow-command[title='Open']");
    await contains(".o-mail-Message-content", { text: "Orange" });
    await contains(".o-mail-Message-content", { text: "Apple" });
    await contains(".o-mail-Message", { count: 0, text: "Banana" });
    assert.verifySteps(["fetch_messages"]);
});

QUnit.test(
    "closing the last visible chat window should unhide the first hidden one",
    async (assert) => {
        const pyEnv = await startServer();
        pyEnv["discuss.channel"].create([
            { name: "channel-A" },
            { name: "channel-B" },
            { name: "channel-C" },
            { name: "channel-D" },
        ]);
        patchUiSize({ width: 900 });
        assert.ok(
            CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 2 + CHAT_WINDOW_INBETWEEN_WIDTH <
                900
        );
        assert.ok(
            CHAT_WINDOW_END_GAP_WIDTH * 2 +
                CHAT_WINDOW_WIDTH * 3 +
                CHAT_WINDOW_INBETWEEN_WIDTH * 2 >
                900
        );
        await start();
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-mail-NotificationItem", { text: "channel-A" });
        await contains(".o-mail-ChatWindow");
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-mail-NotificationItem", { text: "channel-B" });
        await contains(".o-mail-ChatWindow", { count: 2 });
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-mail-NotificationItem", { text: "channel-C" });
        await contains(".o-mail-ChatWindowHiddenToggler", { text: "1" });
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-mail-NotificationItem", { text: "channel-D" });
        await contains(".o-mail-ChatWindowHiddenToggler", { text: "2" });
        await contains(":nth-child(1 of .o-mail-ChatWindow)", { text: "channel-A" });
        await contains(":nth-child(2 of .o-mail-ChatWindow)", { text: "channel-D" });
        await click(".o-mail-ChatWindow-command[title='Close Chat Window']", {
            parent: [".o-mail-ChatWindow", { text: "channel-D" }],
        });
        await contains(":nth-child(1 of .o-mail-ChatWindow)", { text: "channel-A" });
        await contains(":nth-child(2 of .o-mail-ChatWindow)", { text: "channel-C" });
    }
);
