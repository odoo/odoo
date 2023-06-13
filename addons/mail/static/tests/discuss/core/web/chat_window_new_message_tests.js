/* @odoo-module */

import {
    CHAT_WINDOW_END_GAP_WIDTH,
    CHAT_WINDOW_INBETWEEN_WIDTH,
    CHAT_WINDOW_WIDTH,
} from "@mail/core/common/chat_window_service";
import { Command } from "@mail/../tests/helpers/command";
import { patchUiSize } from "@mail/../tests/helpers/patch_ui_size";
import {
    afterNextRender,
    click,
    insertText,
    start,
    startServer,
} from "@mail/../tests/helpers/test_utils";

import { makeDeferred } from "@web/../tests/helpers/utils";

QUnit.module("chat window: new message");

QUnit.test("basic rendering", async (assert) => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button:contains(New Message)");
    assert.containsOnce($, ".o-mail-ChatWindow");
    assert.containsOnce($, ".o-mail-ChatWindow-header");
    assert.containsOnce($, ".o-mail-ChatWindow-header .o-mail-ChatWindow-name");
    assert.strictEqual(
        $(".o-mail-ChatWindow-header .o-mail-ChatWindow-name").text(),
        "New message"
    );
    assert.containsOnce($, ".o-mail-ChatWindow-header .o-mail-ChatWindow-command");
    assert.containsOnce(
        $,
        ".o-mail-ChatWindow-header .o-mail-ChatWindow-command[title='Close Chat Window']"
    );
    assert.containsOnce($, "span:contains('To :')");
    assert.containsOnce($, ".o-discuss-ChannelSelector");
});

QUnit.test("focused on open [REQUIRE FOCUS]", async (assert) => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button:contains(New Message)");
    assert.strictEqual(
        document.activeElement,
        $(".o-mail-ChatWindow .o-discuss-ChannelSelector input")[0]
    );
});

QUnit.test("close", async (assert) => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button:contains(New Message)");
    await click(".o-mail-ChatWindow-header .o-mail-ChatWindow-command[title='Close Chat Window']");
    assert.containsNone($, ".o-mail-ChatWindow");
});

QUnit.test("fold", async (assert) => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button:contains(New Message)");
    assert.containsOnce($, ".o-mail-ChatWindow-content");
    assert.containsOnce($, ".o-discuss-ChannelSelector");

    await click(".o-mail-ChatWindow-header");
    assert.containsNone($, ".o-mail-ChatWindow .o-mail-ChatWindow-content");
    assert.containsNone($, ".o-mail-ChatWindow .o-discuss-ChannelSelector");

    await click(".o-mail-ChatWindow-header");
    assert.containsOnce($, ".o-mail-ChatWindow .o-mail-ChatWindow-content");
    assert.containsOnce($, ".o-discuss-ChannelSelector");
});

QUnit.test(
    'open chat from "new message" chat window should open chat in place of this "new message" chat window',
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Partner 131" });
        pyEnv["res.users"].create({ partner_id: partnerId });
        pyEnv["discuss.channel"].create([
            {
                name: "channel-1",
                channel_member_ids: [
                    Command.create({ is_minimized: true, partner_id: pyEnv.currentPartnerId }),
                ],
            },
            {
                name: "channel-2",
                channel_member_ids: [
                    Command.create({ is_minimized: false, partner_id: pyEnv.currentPartnerId }),
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
        assert.containsNone($, ".o-mail-ChatWindow-header:contains(New message)");

        // open "new message" chat window
        await click(".o_menu_systray i[aria-label='Messages']");
        await click("button:contains(New Message)");
        assert.containsOnce($, ".o-mail-ChatWindow-header:contains(New message)");
        assert.containsN($, ".o-mail-ChatWindow", 2);
        assert.containsOnce($, ".o-mail-ChatWindow .o-discuss-ChannelSelector");
        assert.ok(
            Array.from(document.querySelectorAll(".o-mail-ChatWindow"))
                .pop()
                .textContent.includes("New message")
        );

        // open channel-2
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-mail-NotificationItem .o-mail-NotificationItem-name:contains(channel-2)");
        assert.containsN($, ".o-mail-ChatWindow", 3);
        assert.ok(
            Array.from(document.querySelectorAll(".o-mail-ChatWindow"))[1].textContent.includes(
                "New message"
            )
        );

        // search for a user in "new message" autocomplete
        await afterNextRender(async () => {
            await insertText(".o-discuss-ChannelSelector input", "131");
            await imSearchDef;
        });
        assert.containsOnce($, ".o-discuss-ChannelSelector-suggestion a");
        const $link = $(".o-discuss-ChannelSelector-suggestion a");
        assert.strictEqual($link.text(), "Partner 131");

        await click($link);
        assert.containsNone($, ".o-mail-ChatWindow-header:contains(New message)");
        assert.strictEqual($(".o-mail-ChatWindow-name:eq(1)").text(), "Partner 131");
    }
);

QUnit.test(
    "new message chat window should close on selecting the user if chat with the user is already open",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Partner 131" });
        pyEnv["res.users"].create({ partner_id: partnerId });
        pyEnv["discuss.channel"].create({
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
                Command.create({ partner_id: partnerId }),
            ],
            channel_type: "chat",
            name: "Partner 131",
        });
        await start();
        await click(".o_menu_systray i[aria-label='Messages']");
        await click("button:contains(New Message)");
        await insertText(".o-discuss-ChannelSelector", "131");
        await click(".o-discuss-ChannelSelector-suggestion a");
        assert.containsNone($, ".o-mail-ChatWindow-header:contains(New message)");
        assert.containsOnce($, ".o-mail-ChatWindow");
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
    await click("button:contains(New Message)");
    // search for a user in "new message" autocomplete
    await afterNextRender(async () => {
        await insertText(".o-discuss-ChannelSelector", "131");
        await imSearchDef;
    });
    assert.hasClass($(".o-discuss-ChannelSelector-suggestion a"), "o-mail-NavigableList-active");
});
