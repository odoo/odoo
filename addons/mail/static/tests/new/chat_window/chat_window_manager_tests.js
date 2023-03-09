/** @odoo-module **/

import { patchUiSize } from "@mail/../tests/helpers/patch_ui_size";
import { start, startServer, click, waitUntil } from "@mail/../tests/helpers/test_utils";
import {
    CHAT_WINDOW_END_GAP_WIDTH,
    CHAT_WINDOW_INBETWEEN_WIDTH,
    CHAT_WINDOW_WIDTH,
} from "@mail/new/web/chat_window/chat_window_service";

QUnit.module("chat window manager");

QUnit.test("chat window does not fetch messages if hidden", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create([
        {
            channel_member_ids: [
                [0, 0, { is_minimized: true, partner_id: pyEnv.currentPartnerId }],
            ],
        },
        {
            channel_member_ids: [
                [0, 0, { is_minimized: true, partner_id: pyEnv.currentPartnerId }],
            ],
        },
        {
            channel_member_ids: [
                [0, 0, { is_minimized: true, partner_id: pyEnv.currentPartnerId }],
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
            if (route === "/mail/channel/messages") {
                assert.step("fetch_messages");
            }
        },
    });
    assert.containsN($, ".o-mail-chat-window", 2);
    assert.containsOnce($, ".o-mail-chat-window-hidden-button");
    assert.verifySteps(["fetch_messages", "fetch_messages"]);
});

QUnit.test("click on hidden chat window should fetch its messages", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create([
        {
            channel_member_ids: [
                [0, 0, { is_minimized: true, partner_id: pyEnv.currentPartnerId }],
            ],
        },
        {
            channel_member_ids: [
                [0, 0, { is_minimized: true, partner_id: pyEnv.currentPartnerId }],
            ],
        },
        {
            channel_member_ids: [
                [0, 0, { is_minimized: true, partner_id: pyEnv.currentPartnerId }],
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
            if (route === "/mail/channel/messages") {
                assert.step("fetch_messages");
            }
        },
    });
    assert.containsN($, ".o-mail-chat-window", 2);
    assert.containsOnce($, ".o-mail-chat-window-hidden-button");
    assert.verifySteps(["fetch_messages", "fetch_messages"]);
    await click(".o-mail-chat-window-hidden-button");
    await click(".o-mail-chat-window-hidden-menu-item .o-mail-chat-window-header");
    assert.verifySteps(["fetch_messages"]);
});

QUnit.test(
    "closing the last visible chat window should unhide the first hidden one",
    async (assert) => {
        const pyEnv = await startServer();
        pyEnv["mail.channel"].create([
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
        await click(".o-mail-notification-item:contains(channel-A)");
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-mail-notification-item:contains(channel-B)");
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-mail-notification-item:contains(channel-C)");
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-mail-notification-item:contains(channel-D)");
        await waitUntil(
            ".o-mail-chat-window-header:contains(channel-D) .o-mail-command[title='Close chat window']"
        );
        assert.containsN($, ".o-mail-chat-window", 2);
        assert.containsOnce($, ".o-mail-chat-window:eq(0):contains(channel-A)");
        assert.containsOnce($, ".o-mail-chat-window:eq(1):contains(channel-D)");
        assert.containsOnce($, ".o-mail-chat-window-hidden-button:contains(2)");
        await click(
            ".o-mail-chat-window-header:contains(channel-D) .o-mail-command[title='Close chat window']"
        );
        assert.containsOnce($, ".o-mail-chat-window:eq(0):contains(channel-A)");
        assert.containsOnce($, ".o-mail-chat-window:eq(1):contains(channel-C)");
    }
);
