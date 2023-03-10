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
    await click(".o-MessagingMenu-new");
    assert.containsOnce($, ".o-ChatWindow");
    assert.containsOnce($, ".o-ChatWindow-header");
    assert.containsOnce($, ".o-ChatWindow-header .o-ChatWindow-name");
    assert.strictEqual($(".o-ChatWindow-header .o-ChatWindow-name").text(), "New message");
    assert.containsOnce($, ".o-ChatWindow-header .o-ChatWindow-command");
    assert.containsOnce($, ".o-ChatWindow-header .o-ChatWindow-command[title='Close chat window']");
    assert.containsOnce($, "span:contains('To :')");
    assert.containsOnce($, ".o-ChannelSelector");
});

QUnit.test("focused on open [REQUIRE FOCUS]", async (assert) => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-MessagingMenu-new");
    assert.strictEqual(document.activeElement, $(".o-ChatWindow .o-ChannelSelector input")[0]);
});

QUnit.test("close", async (assert) => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-MessagingMenu-new");
    await click(".o-ChatWindow-header .o-ChatWindow-command[title='Close chat window']");
    assert.containsNone($, ".o-ChatWindow");
});

QUnit.test("fold", async (assert) => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-MessagingMenu-new");
    assert.containsOnce($, ".o-ChatWindow-content");
    assert.containsOnce($, ".o-ChannelSelector");

    await click(".o-ChatWindow-header");
    assert.containsNone($, ".o-ChatWindow .o-ChatWindow-content");
    assert.containsNone($, ".o-ChatWindow .o-ChannelSelector");

    await click(".o-ChatWindow-header");
    assert.containsOnce($, ".o-ChatWindow .o-ChatWindow-content");
    assert.containsOnce($, ".o-ChannelSelector");
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
        assert.containsNone($, ".o-ChatWindow-header:contains(New message)");

        // open "new message" chat window
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-MessagingMenu-new");
        assert.containsOnce($, ".o-ChatWindow-header:contains(New message)");
        assert.containsN($, ".o-ChatWindow", 2);
        assert.containsOnce($, ".o-ChatWindow .o-ChannelSelector");
        assert.ok(
            Array.from(document.querySelectorAll(".o-ChatWindow"))
                .pop()
                .textContent.includes("New message")
        );

        // open channel-2
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-NotificationItem .o-NotificationItem-name:contains(channel-2)");
        assert.containsN($, ".o-ChatWindow", 3);
        assert.ok(
            Array.from(document.querySelectorAll(".o-ChatWindow"))[1].textContent.includes(
                "New message"
            )
        );

        // search for a user in "new message" autocomplete
        await afterNextRender(async () => {
            await insertText(".o-ChannelSelector input", "131");
            await imSearchDef;
        });
        assert.containsOnce($, ".o-ChannelSelector-suggestion a");
        const $link = $(".o-ChannelSelector-suggestion a");
        assert.strictEqual($link.text(), "Partner 131");

        await click($link);
        assert.containsNone($, ".o-ChatWindow-header:contains(New message)");
        assert.strictEqual($(".o-ChatWindow-name:eq(1)").text(), "Partner 131");
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
        await click(".o-MessagingMenu-new");
        await insertText(".o-ChannelSelector", "131");
        await click(".o-ChannelSelector-suggestion a");
        assert.containsNone($, ".o-ChatWindow-header:contains(New message)");
        assert.containsOnce($, ".o-ChatWindow");
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
    await click(".o-MessagingMenu-new");
    // search for a user in "new message" autocomplete
    await afterNextRender(async () => {
        await insertText(".o-ChannelSelector", "131");
        await imSearchDef;
    });
    assert.hasClass($(".o-ChannelSelector-suggestion a"), "o-NavigableList-active");
});
