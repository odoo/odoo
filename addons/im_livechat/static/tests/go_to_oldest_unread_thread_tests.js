/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { insertText, contains } from "@bus/../tests/helpers/test_utils";

import { Command } from "@mail/../tests/helpers/command";
import { nextTick, triggerHotkey } from "@web/../tests/helpers/utils";
import { patchUiSize } from "@mail/../tests/helpers/patch_ui_size";

import { start } from "@mail/../tests/helpers/test_utils";

QUnit.module("go to oldest unread livechat");

QUnit.test("tab on discuss composer goes to oldest unread livechat", async () => {
    const pyEnv = await startServer();
    const channelIds = pyEnv["discuss.channel"].create([
        {
            anonymous_name: "Visitor 11",
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: pyEnv.publicPartnerId }),
            ],
            channel_type: "livechat",
            livechat_operator_id: pyEnv.currentPartnerId,
            name: "Livechat 1",
        },
        {
            anonymous_name: "Visitor 12",
            channel_member_ids: [
                Command.create({
                    partner_id: pyEnv.currentPartnerId,
                    message_unread_counter: 1,
                    last_interest_dt: "2021-01-02 10:00:00",
                }),
                Command.create({ partner_id: pyEnv.publicPartnerId }),
            ],
            channel_type: "livechat",
            livechat_operator_id: pyEnv.currentPartnerId,
            name: "Livechat 2",
        },
        {
            anonymous_name: "Visitor 13",
            channel_member_ids: [
                Command.create({
                    partner_id: pyEnv.currentPartnerId,
                    message_unread_counter: 1,
                    last_interest_dt: "2021-01-01 10:00:00",
                }),
                Command.create({ partner_id: pyEnv.publicPartnerId }),
            ],
            channel_type: "livechat",
            livechat_operator_id: pyEnv.currentPartnerId,
            name: "Livechat 3",
        },
    ]);
    pyEnv["mail.message"].create([
        {
            author_id: pyEnv.publicPartnerId,
            body: "Hello",
            model: "discuss.channel",
            res_id: channelIds[1],
        },
        {
            author_id: pyEnv.publicPartnerId,
            body: "Hello",
            model: "discuss.channel",
            res_id: channelIds[2],
        },
    ]);

    const { openDiscuss } = await start();
    await openDiscuss(channelIds[0]);

    await contains(".o-mail-DiscussSidebarChannel.o-active", { text: "Visitor 11" });
    await contains(".o-mail-Composer-footer", { text: "Tab to next livechat" });
    document.querySelector(".o-mail-Composer-input").focus();
    await contains(".o-active .o-mail-DiscussSidebar-badge", { count: 0 });
    triggerHotkey("Tab");
    await contains(".o-mail-DiscussSidebarChannel.o-active", { text: "Visitor 13" });
    document.querySelector(".o-mail-Composer-input").focus();
    await contains(".o-active .o-mail-DiscussSidebar-badge", { count: 0 });
    triggerHotkey("Tab");
    await contains(".o-mail-DiscussSidebarChannel.o-active", { text: "Visitor 12" });
});

QUnit.test("switching to folded chat window unfolds it", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([
        {
            anonymous_name: "Visitor 11",
            channel_member_ids: [
                Command.create({
                    partner_id: pyEnv.currentPartnerId,
                    fold_state: "open",
                    is_minimized: true,
                }),
                Command.create({ partner_id: pyEnv.publicPartnerId }),
            ],
            channel_type: "livechat",
            livechat_operator_id: pyEnv.currentPartnerId,
            name: "Livechat 1",
        },
        {
            anonymous_name: "Visitor 12",
            channel_member_ids: [
                Command.create({
                    partner_id: pyEnv.currentPartnerId,
                    fold_state: "folded",
                    is_minimized: true,
                    message_unread_counter: 1,
                    last_interest_dt: "2021-01-02 10:00:00",
                }),
                Command.create({ partner_id: pyEnv.publicPartnerId }),
            ],
            channel_type: "livechat",
            livechat_operator_id: pyEnv.currentPartnerId,
            name: "Livechat 2",
        },
    ]);
    await start();
    await contains(".o-mail-ChatWindow.o-folded .o-mail-ChatWindow-name:contains(Visitor 12)");
    $(".o-mail-ChatWindow:contains(Visitor 11) .o-mail-Composer-input").trigger("focus");
    triggerHotkey("Tab");
    await contains(
        ".o-mail-ChatWindow:not(.o-folded) .o-mail-ChatWindow-name:contains(Visitor 12)"
    );
    assert.strictEqual(
        document.activeElement,
        $(".o-mail-ChatWindow:contains(Visitor 12) .o-mail-Composer-input")[0]
    );
});

QUnit.test("switching to hidden chat window unhides it", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([
        {
            anonymous_name: "Visitor 11",
            channel_member_ids: [
                Command.create({
                    partner_id: pyEnv.currentPartnerId,
                    is_minimized: true,
                }),
                Command.create({ partner_id: pyEnv.publicPartnerId }),
            ],
            channel_type: "livechat",
            livechat_operator_id: pyEnv.currentPartnerId,
            name: "Livechat 1",
        },
        {
            anonymous_name: "Visitor 12",
            channel_member_ids: [
                Command.create({
                    partner_id: pyEnv.currentPartnerId,
                    is_minimized: true,
                    message_unread_counter: 1,
                    last_interest_dt: "2021-01-02 10:00:00",
                }),
                Command.create({ partner_id: pyEnv.publicPartnerId }),
            ],
            channel_type: "livechat",
            livechat_operator_id: pyEnv.currentPartnerId,
            name: "Livechat 2",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId, is_minimized: true }),
            ],
        },
    ]);
    patchUiSize({ width: 900 }); // enough for 2 chat windows
    await start();
    assert.containsNone(
        $,
        ".o-mail-ChatWindow.o-folded .o-mail-ChatWindow-name:contains(Visitor 12)"
    );
    $(".o-mail-ChatWindow:contains(Visitor 11) .o-mail-Composer-input").trigger("focus");
    triggerHotkey("Tab");
    await contains(
        ".o-mail-ChatWindow:not(.o-folded) .o-mail-ChatWindow-name:contains(Visitor 12)"
    );
    assert.strictEqual(
        document.activeElement,
        $(".o-mail-ChatWindow:contains(Visitor 12) .o-mail-Composer-input")[0]
    );
});

QUnit.test("tab on composer doesn't switch thread if user is typing", async () => {
    const pyEnv = await startServer();
    const channelIds = pyEnv["discuss.channel"].create([
        {
            anonymous_name: "Visitor 11",
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: pyEnv.publicPartnerId }),
            ],
            channel_type: "livechat",
            livechat_operator_id: pyEnv.currentPartnerId,
            name: "Livechat 1",
        },
        {
            anonymous_name: "Visitor 12",
            channel_member_ids: [
                Command.create({
                    partner_id: pyEnv.currentPartnerId,
                    message_unread_counter: 1,
                    last_interest_dt: "2021-01-02 10:00:00",
                }),
                Command.create({ partner_id: pyEnv.publicPartnerId }),
            ],
            channel_type: "livechat",
            livechat_operator_id: pyEnv.currentPartnerId,
            name: "Livechat 2",
        },
    ]);

    const { openDiscuss } = await start();
    await openDiscuss(channelIds[0]);
    await insertText(".o-mail-Composer-input", "Hello, ");
    triggerHotkey("Tab");
    await nextTick();
    await contains(".o-mail-DiscussSidebarChannel.o-active:contains(Visitor 11)");
});

QUnit.test("tab on composer doesn't switch thread if no unread thread", async (assert) => {
    const pyEnv = await startServer();
    const channelIds = pyEnv["discuss.channel"].create([
        {
            anonymous_name: "Visitor 11",
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: pyEnv.publicPartnerId }),
            ],
            channel_type: "livechat",
            livechat_operator_id: pyEnv.currentPartnerId,
            name: "Livechat 1",
        },
        {
            anonymous_name: "Visitor 12",
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: pyEnv.publicPartnerId }),
            ],
            channel_type: "livechat",
            livechat_operator_id: pyEnv.currentPartnerId,
            name: "Livechat 2",
        },
    ]);

    const { openDiscuss } = await start();
    await openDiscuss(channelIds[0]);
    document.querySelector(".o-mail-Composer-input").focus();
    triggerHotkey("Tab");
    await nextTick();
    await contains(".o-mail-DiscussSidebarChannel.o-active:contains(Visitor 11)");
});
