/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Command } from "@mail/../tests/helpers/command";
import { nextTick, triggerHotkey } from "@web/../tests/helpers/utils";
import { patchUiSize } from "@mail/../tests/helpers/patch_ui_size";

import { afterNextRender, insertText, start } from "@mail/../tests/helpers/test_utils";

QUnit.module("go to oldest unread livechat");

QUnit.test("tab on discuss composer goes to oldest unread livechat", async (assert) => {
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

    assert.containsOnce($, ".o-mail-DiscussCategoryItem.o-active:contains(Visitor 11)");
    assert.containsOnce(
        $,
        ".o-mail-Composer-footer:contains(Tab to next livechat)"
    );
    await afterNextRender(() => {
        document.querySelector(".o-mail-Composer-input").focus();
        triggerHotkey("Tab");
    });
    assert.containsOnce($, ".o-mail-DiscussCategoryItem.o-active:contains(Visitor 13)");
    await afterNextRender(() => {
        document.querySelector(".o-mail-Composer-input").focus();
        triggerHotkey("Tab");
    });
    assert.containsOnce($, ".o-mail-DiscussCategoryItem.o-active:contains(Visitor 12)");
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
    assert.containsOnce(
        $,
        ".o-mail-ChatWindow.o-folded .o-mail-ChatWindow-header:contains(Visitor 12)"
    );
    await afterNextRender(() => {
        $(".o-mail-ChatWindow:contains(Visitor 11) .o-mail-Composer-input").trigger("focus");
        triggerHotkey("Tab");
    });
    assert.containsOnce(
        $,
        ".o-mail-ChatWindow:not(.o-folded) .o-mail-ChatWindow-header:contains(Visitor 12)"
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
        ".o-mail-ChatWindow.o-folded .o-mail-ChatWindow-header:contains(Visitor 12)"
    );
    await afterNextRender(() => {
        $(".o-mail-ChatWindow:contains(Visitor 11) .o-mail-Composer-input").trigger("focus");
        triggerHotkey("Tab");
    });
    assert.containsOnce(
        $,
        ".o-mail-ChatWindow:not(.o-folded) .o-mail-ChatWindow-header:contains(Visitor 12)"
    );
    assert.strictEqual(
        document.activeElement,
        $(".o-mail-ChatWindow:contains(Visitor 12) .o-mail-Composer-input")[0]
    );
});

QUnit.test("tab on composer doesn't switch thread if user is typing", async (assert) => {
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
    assert.containsOnce($, ".o-mail-DiscussCategoryItem.o-active:contains(Visitor 11)");
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
    assert.containsOnce($, ".o-mail-DiscussCategoryItem.o-active:contains(Visitor 11)");
});
