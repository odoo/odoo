/* @odoo-module */

import {
    CHAT_WINDOW_END_GAP_WIDTH,
    CHAT_WINDOW_INBETWEEN_WIDTH,
    CHAT_WINDOW_WIDTH,
} from "@mail/core/common/chat_window_service";
import { Command } from "@mail/../tests/helpers/command";
import { patchUiSize } from "@mail/../tests/helpers/patch_ui_size";
import { start, startServer, click, waitUntil } from "@mail/../tests/helpers/test_utils";

QUnit.module("chat window manager");

QUnit.test("chat window does not fetch messages if hidden", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([
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
    assert.containsN($, ".o-mail-ChatWindow", 2);
    assert.containsOnce($, ".o-mail-ChatWindowHiddenToggler");
    assert.verifySteps(["fetch_messages", "fetch_messages"]);
});

QUnit.test("click on hidden chat window should fetch its messages", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([
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
    assert.containsN($, ".o-mail-ChatWindow", 2);
    assert.containsOnce($, ".o-mail-ChatWindowHiddenToggler");
    assert.verifySteps(["fetch_messages", "fetch_messages"]);
    await click(".o-mail-ChatWindowHiddenToggler");
    await click(".o-mail-ChatWindowHiddenMenu-item .o-mail-ChatWindow-command[title='Open']");
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
        await click(".o-mail-NotificationItem:contains(channel-A)");
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-mail-NotificationItem:contains(channel-B)");
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-mail-NotificationItem:contains(channel-C)");
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-mail-NotificationItem:contains(channel-D)");
        await waitUntil(
            ".o-mail-ChatWindow-header:contains(channel-D) .o-mail-ChatWindow-command[title='Close Chat Window']"
        );
        assert.containsN($, ".o-mail-ChatWindow", 2);
        assert.containsOnce($, ".o-mail-ChatWindow:eq(0):contains(channel-A)");
        assert.containsOnce($, ".o-mail-ChatWindow:eq(1):contains(channel-D)");
        assert.containsOnce($, ".o-mail-ChatWindowHiddenToggler:contains(2)");
        await click(
            ".o-mail-ChatWindow-header:contains(channel-D) .o-mail-ChatWindow-command[title='Close Chat Window']"
        );
        assert.containsOnce($, ".o-mail-ChatWindow:eq(0):contains(channel-A)");
        assert.containsOnce($, ".o-mail-ChatWindow:eq(1):contains(channel-C)");
    }
);
