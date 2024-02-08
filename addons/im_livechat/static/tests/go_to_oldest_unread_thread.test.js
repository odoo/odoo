import {
    contains,
    focus,
    insertText,
    openDiscuss,
    patchUiSize,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { defineLivechatModels } from "./livechat_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("tab on discuss composer goes to oldest unread livechat", async () => {
    const pyEnv = await startServer();
    const guestId_1 = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const guestId_2 = pyEnv["mail.guest"].create({ name: "Visitor 12" });
    const guestId_3 = pyEnv["mail.guest"].create({ name: "Visitor 13" });
    const channelIds = pyEnv["discuss.channel"].create([
        {
            anonymous_name: "Visitor 11",
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ guest_id: guestId_1 }),
            ],
            channel_type: "livechat",
            livechat_operator_id: serverState.partnerId,
            name: "Livechat 1",
        },
        {
            anonymous_name: "Visitor 12",
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                    message_unread_counter: 1,
                    last_interest_dt: "2021-01-02 10:00:00",
                }),
                Command.create({ guest_id: guestId_2 }),
            ],
            channel_type: "livechat",
            livechat_operator_id: serverState.partnerId,
            name: "Livechat 2",
        },
        {
            anonymous_name: "Visitor 13",
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                    message_unread_counter: 1,
                    last_interest_dt: "2021-01-01 10:00:00",
                }),
                Command.create({ guest_id: guestId_3 }),
            ],
            channel_type: "livechat",
            livechat_operator_id: serverState.partnerId,
            name: "Livechat 3",
        },
    ]);
    pyEnv["mail.message"].create([
        {
            author_guest_id: guestId_2,
            body: "Hello",
            model: "discuss.channel",
            res_id: channelIds[1],
        },
        {
            author_guest_id: guestId_3,
            body: "Hello",
            model: "discuss.channel",
            res_id: channelIds[2],
        },
    ]);
    await start();
    await openDiscuss(channelIds[0]);
    await contains(".o-mail-DiscussSidebarChannel.o-active", { text: "Visitor 11" });
    await contains(".o-mail-Composer-footer", { text: "Tab to next livechat" });
    await focus(".o-mail-Composer-input");
    await contains(".o-active .o-mail-DiscussSidebar-badge", { count: 0 });
    triggerHotkey("Tab");
    await contains(".o-mail-DiscussSidebarChannel.o-active", { text: "Visitor 13" });
    await focus(".o-mail-Composer-input");
    await contains(".o-active .o-mail-DiscussSidebar-badge", { count: 0 });
    triggerHotkey("Tab");
    await contains(".o-mail-DiscussSidebarChannel.o-active", { text: "Visitor 12" });
});

test("switching to folded chat window unfolds it [REQUIRE FOCUS]", async () => {
    const pyEnv = await startServer();
    const guestId_1 = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const guestId_2 = pyEnv["mail.guest"].create({ name: "Visitor 12" });
    const channelIds = pyEnv["discuss.channel"].create([
        {
            anonymous_name: "Visitor 11",
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                    fold_state: "open",
                }),
                Command.create({ guest_id: guestId_1 }),
            ],
            channel_type: "livechat",
            livechat_operator_id: serverState.partnerId,
            name: "Livechat 1",
        },
        {
            anonymous_name: "Visitor 12",
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                    fold_state: "folded",
                    last_interest_dt: "2021-01-02 10:00:00",
                }),
                Command.create({ guest_id: guestId_2 }),
            ],
            channel_type: "livechat",
            livechat_operator_id: serverState.partnerId,
            name: "Livechat 2",
        },
    ]);
    pyEnv["mail.message"].create({
        author_guest_id: guestId_2,
        body: "Hello",
        model: "discuss.channel",
        res_id: channelIds[1],
    });
    await start();
    await contains(".o-mail-ChatBubble[name='Visitor 12']");
    await focus(".o-mail-Composer-input", {
        parent: [".o-mail-ChatWindow", { text: "Visitor 11" }],
    });
    triggerHotkey("Tab");
    await contains(".o-mail-ChatWindow", {
        text: "Visitor 12",
        contains: [".o-mail-Composer-input:focus"],
    });
});

test("switching to hidden chat window unhides it [REQUIRE FOCUS]", async () => {
    const pyEnv = await startServer();
    const [guestId_1, guestId_2] = pyEnv["mail.guest"].create([
        { name: "Visitor 11" },
        { name: "Visitor 12" },
    ]);
    const [livechat_1] = pyEnv["discuss.channel"].create([
        {
            anonymous_name: "Visitor 11",
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                    fold_state: "open",
                }),
                Command.create({ guest_id: guestId_1 }),
            ],
            channel_type: "livechat",
            livechat_operator_id: serverState.partnerId,
            name: "Livechat 1",
        },
        {
            anonymous_name: "Visitor 12",
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                    fold_state: "open",
                    last_interest_dt: "2021-01-02 10:00:00",
                }),
                Command.create({ guest_id: guestId_2 }),
            ],
            channel_type: "livechat",
            livechat_operator_id: serverState.partnerId,
            name: "Livechat 2",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId, fold_state: "open" }),
            ],
            name: "general",
        },
    ]);
    pyEnv["mail.message"].create({
        author_guest_id: guestId_2,
        body: "Hello",
        model: "discuss.channel",
        res_id: livechat_1,
    });
    patchUiSize({ width: 900 }); // enough for 2 chat windows max
    await start();
    // FIXME: expected order: general, 12, 11
    await contains(".o-mail-ChatWindow", { count: 2 });
    await contains(".o-mail-ChatWindow", { count: 0, text: "Visitor 11" });
    await focus(".o-mail-Composer-input", {
        parent: [".o-mail-ChatWindow", { text: "Visitor 12" }],
    });
    triggerHotkey("Tab");
    await contains(".o-mail-ChatWindow", {
        text: "Visitor 11",
        contains: [".o-mail-Composer-input:focus"],
    });
});

test("tab on composer doesn't switch thread if user is typing", async () => {
    const pyEnv = await startServer();
    const guestId_1 = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const guestId_2 = pyEnv["mail.guest"].create({ name: "Visitor 12" });
    const channelIds = pyEnv["discuss.channel"].create([
        {
            anonymous_name: "Visitor 11",
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ guest_id: guestId_1 }),
            ],
            channel_type: "livechat",
            livechat_operator_id: serverState.partnerId,
            name: "Livechat 1",
        },
        {
            anonymous_name: "Visitor 12",
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                    message_unread_counter: 1,
                    last_interest_dt: "2021-01-02 10:00:00",
                }),
                Command.create({ guest_id: guestId_2 }),
            ],
            channel_type: "livechat",
            livechat_operator_id: serverState.partnerId,
            name: "Livechat 2",
        },
    ]);
    await start();
    await openDiscuss(channelIds[0]);
    await insertText(".o-mail-Composer-input", "Hello, ");
    triggerHotkey("Tab");
    await contains(".o-mail-DiscussSidebarChannel.o-active", { text: "Visitor 11" });
});

test("tab on composer doesn't switch thread if no unread thread", async () => {
    const pyEnv = await startServer();
    const guestId_1 = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const guestId_2 = pyEnv["mail.guest"].create({ name: "Visitor 12" });
    const channelIds = pyEnv["discuss.channel"].create([
        {
            anonymous_name: "Visitor 11",
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ guest_id: guestId_1 }),
            ],
            channel_type: "livechat",
            livechat_operator_id: serverState.partnerId,
            name: "Livechat 1",
        },
        {
            anonymous_name: "Visitor 12",
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ guest_id: guestId_2 }),
            ],
            channel_type: "livechat",
            livechat_operator_id: serverState.partnerId,
            name: "Livechat 2",
        },
    ]);
    await start();
    await openDiscuss(channelIds[0]);
    await focus(".o-mail-Composer-input");
    triggerHotkey("Tab");
    await contains(".o-mail-DiscussSidebarChannel.o-active", { text: "Visitor 11" });
});
