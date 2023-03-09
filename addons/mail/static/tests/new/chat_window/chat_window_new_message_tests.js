/** @odoo-module **/

import { patchUiSize } from "@mail/../tests/helpers/patch_ui_size";
import {
    afterNextRender,
    click,
    insertText,
    start,
    startServer,
} from "@mail/../tests/helpers/test_utils";
import { makeDeferred } from "@web/../tests/helpers/utils";
import {
    CHAT_WINDOW_END_GAP_WIDTH,
    CHAT_WINDOW_INBETWEEN_WIDTH,
    CHAT_WINDOW_WIDTH,
} from "@mail/new/web/chat_window/chat_window_service";

QUnit.module("chat window: new message");

QUnit.test("basic rendering", async (assert) => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-messaging-menu-new-message");
    assert.containsOnce($, ".o-mail-chat-window");
    assert.containsOnce($, ".o-mail-chat-window-header");
    assert.containsOnce($, ".o-mail-chat-window-header .o-mail-chat-window-header-name");
    assert.strictEqual(
        $(".o-mail-chat-window-header .o-mail-chat-window-header-name").text(),
        "New message"
    );
    assert.containsOnce($, ".o-mail-chat-window-header .o-mail-command");
    assert.containsOnce($, ".o-mail-chat-window-header .o-mail-command[title='Close chat window']");
    assert.containsOnce($, "span:contains('To :')");
    assert.containsOnce($, ".o-mail-channel-selector");
});

QUnit.test("focused on open [REQUIRE FOCUS]", async (assert) => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-messaging-menu-new-message");
    assert.strictEqual(
        document.activeElement,
        $(".o-mail-chat-window .o-mail-channel-selector input")[0]
    );
});

QUnit.test("close", async (assert) => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-messaging-menu-new-message");
    await click(".o-mail-chat-window-header .o-mail-command[title='Close chat window']");
    assert.containsNone($, ".o-mail-chat-window");
});

QUnit.test("fold", async (assert) => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-messaging-menu-new-message");
    assert.containsOnce($, ".o-mail-chat-window-content");
    assert.containsOnce($, ".o-mail-channel-selector");

    await click(".o-mail-chat-window-header");
    assert.containsNone($, ".o-mail-chat-window .o-mail-chat-window-content");
    assert.containsNone($, ".o-mail-chat-window .o-mail-channel-selector");

    await click(".o-mail-chat-window-header");
    assert.containsOnce($, ".o-mail-chat-window .o-mail-chat-window-content");
    assert.containsOnce($, ".o-mail-channel-selector");
});

QUnit.test(
    'open chat from "new message" chat window should open chat in place of this "new message" chat window',
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Partner 131" });
        pyEnv["res.users"].create({ partner_id: partnerId });
        pyEnv["mail.channel"].create([
            {
                name: "channel-1",
                channel_member_ids: [
                    [0, 0, { is_minimized: true, partner_id: pyEnv.currentPartnerId }],
                ],
            },
            {
                name: "channel-2",
                channel_member_ids: [
                    [0, 0, { is_minimized: false, partner_id: pyEnv.currentPartnerId }],
                ],
            },
        ]);
        const imSearchDef = makeDeferred();
        patchUiSize({ width: 1920 });
        assert.ok(
            CHAT_WINDOW_END_GAP_WIDTH * 2 +
                CHAT_WINDOW_WIDTH * 3 +
                CHAT_WINDOW_INBETWEEN_WIDTH * 2 <
                1920,
            "should have enough space to open 3 chat windows simultaneously"
        );
        await start({
            mockRPC(route, args) {
                if (args.method === "im_search") {
                    imSearchDef.resolve();
                }
            },
        });
        assert.containsNone($, ".o-mail-chat-window-header:contains(New message)");

        // open "new message" chat window
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-mail-messaging-menu-new-message");
        assert.containsOnce($, ".o-mail-chat-window-header:contains(New message)");
        assert.containsN($, ".o-mail-chat-window", 2);
        assert.containsOnce($, ".o-mail-chat-window .o-mail-channel-selector");
        assert.ok(
            Array.from(document.querySelectorAll(".o-mail-chat-window"))
                .pop()
                .textContent.includes("New message")
        );

        // open channel-2
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-mail-notification-item .o-mail-notification-item-name:contains(channel-2)");
        assert.containsN($, ".o-mail-chat-window", 3);
        assert.ok(
            Array.from(document.querySelectorAll(".o-mail-chat-window"))[1].textContent.includes(
                "New message"
            )
        );

        // search for a user in "new message" autocomplete
        await afterNextRender(async () => {
            await insertText(".o-mail-channel-selector input", "131");
            await imSearchDef;
        });
        assert.containsOnce($, ".o-mail-channel-selector-suggestion a");
        const $link = $(".o-mail-channel-selector-suggestion a");
        assert.strictEqual($link.text(), "Partner 131");

        await click($link);
        assert.containsNone($, ".o-mail-chat-window-header:contains(New message)");
        assert.strictEqual($(".o-mail-chat-window-header-name:eq(1)").text(), "Partner 131");
    }
);

QUnit.test(
    "new message chat window should close on selecting the user if chat with the user is already open",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Partner 131" });
        pyEnv["res.users"].create({ partner_id: partnerId });
        pyEnv["mail.channel"].create({
            channel_member_ids: [
                [
                    0,
                    0,
                    {
                        fold_state: "open",
                        is_minimized: true,
                        partner_id: pyEnv.currentPartnerId,
                    },
                ],
                [0, 0, { partner_id: partnerId }],
            ],
            channel_type: "chat",
            name: "Partner 131",
        });
        await start();
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-mail-messaging-menu-new-message");
        await insertText(".o-mail-channel-selector", "131");
        await click(".o-mail-channel-selector-suggestion a");
        assert.containsNone($, ".o-mail-chat-window-header:contains(New message)");
        assert.containsOnce($, ".o-mail-chat-window");
    }
);

QUnit.test("new message autocomplete should automatically select first result", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Partner 131" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const imSearchDef = makeDeferred();
    await start({
        mockRPC(route, args) {
            if (args.method === "im_search") {
                imSearchDef.resolve();
            }
        },
    });
    // open "new message" chat window
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-messaging-menu-new-message");
    // search for a user in "new message" autocomplete
    await afterNextRender(async () => {
        await insertText(".o-mail-channel-selector", "131");
        await imSearchDef;
    });
    assert.hasClass($(".o-mail-channel-selector-suggestion a"), "o-navigable-list-active-item");
});
