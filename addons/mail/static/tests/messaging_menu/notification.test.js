import { describe, expect, test } from "@odoo/hoot";
import {
    assertSteps,
    click,
    contains,
    defineMailModels,
    start,
    startServer,
    step,
    triggerEvents,
} from "../mail_test_helpers";
import { Command, mockService, serverState } from "@web/../tests/web_test_helpers";
import { getMockEnv } from "@web/../tests/_framework/env_test_helpers";
import { actionService } from "@web/webclient/actions/action_service";

describe.current.tags("desktop");
defineMailModels();

test("basic layout", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    const messageId = pyEnv["mail.message"].create({
        message_type: "email",
        model: "discuss.channel",
        res_id: channelId,
    });
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId,
            notification_status: "exception",
            notification_type: "email",
        },
        {
            mail_message_id: messageId,
            notification_status: "exception",
            notification_type: "email",
        },
    ]);
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", {
        contains: [
            [".o-mail-NotificationItem-name", { text: "Discussion Channel" }],
            [".o-mail-NotificationItem-counter", { text: "2" }],
            [".o-mail-NotificationItem-date", { text: "now" }],
            [
                ".o-mail-NotificationItem-text",
                {
                    text: "An error occurred when sending an email",
                },
            ],
        ],
    });
});

test("mark as read", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    const messageId = pyEnv["mail.message"].create({
        message_type: "email",
        model: "discuss.channel",
        res_id: channelId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "exception",
        notification_type: "email",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await triggerEvents(".o-mail-NotificationItem", ["mouseenter"], { text: "Discussion Channel" });
    await click(".o-mail-NotificationItem-markAsRead", {
        parent: [".o-mail-NotificationItem", { text: "Discussion Channel" }],
    });
    await contains(".o-mail-NotificationItem", { count: 0, text: "Discussion Channel" });
});

test("open non-channel failure", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([{}, {}]);
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            message_type: "email",
            model: "res.partner",
            res_id: partnerId_1,
        },
        {
            message_type: "email",
            model: "res.partner",
            res_id: partnerId_2,
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId_1,
            notification_status: "exception",
            notification_type: "email",
        },
        {
            mail_message_id: messageId_2,
            notification_status: "bounce",
            notification_type: "email",
        },
    ]);
    mockService("action", () => ({
        ...actionService.start(getMockEnv()),
        doAction(action) {
            step("do_action");
            expect(action.name).toBe("Mail Failures");
            expect(action.type).toBe("ir.actions.act_window");
            expect(action.view_mode).toBe("kanban,list,form");
            expect(JSON.stringify(action.views)).toBe(
                JSON.stringify([
                    [false, "kanban"],
                    [false, "list"],
                    [false, "form"],
                ])
            );
            expect(action.target).toBe("current");
            expect(action.res_model).toBe("res.partner");
            expect(JSON.stringify(action.domain)).toBe(
                JSON.stringify([["message_has_error", "=", true]])
            );
        },
    }));
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await assertSteps(["do_action"]);
});

test("different discuss.channel are not grouped", async () => {
    const pyEnv = await startServer();
    const [channelId_1, channelId_2] = pyEnv["discuss.channel"].create([
        { name: "Channel_1" },
        { name: "Channel_2" },
    ]);
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            message_type: "email",
            model: "discuss.channel",
            res_id: channelId_1,
        },
        {
            message_type: "email",
            model: "discuss.channel",
            res_id: channelId_2,
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId_1,
            notification_status: "exception",
            notification_type: "email",
        },
        {
            mail_message_id: messageId_1,
            notification_status: "exception",
            notification_type: "email",
        },
        {
            mail_message_id: messageId_2,
            notification_status: "bounce",
            notification_type: "email",
        },
        {
            mail_message_id: messageId_2,
            notification_status: "bounce",
            notification_type: "email",
        },
    ]);
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem-text", {
        count: 2,
        text: "An error occurred when sending an email",
    });
});

test("multiple grouped notifications by model", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const companyId = pyEnv["res.company"].create({});
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            message_type: "email",
            model: "res.partner",
            res_id: partnerId,
        },
        {
            message_type: "email",
            model: "res.company",
            res_id: companyId,
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId_1,
            notification_status: "exception",
            notification_type: "email",
        },
        {
            mail_message_id: messageId_1,
            notification_status: "exception",
            notification_type: "email",
        },
        {
            mail_message_id: messageId_2,
            notification_status: "bounce",
            notification_type: "email",
        },
        {
            mail_message_id: messageId_2,
            notification_status: "bounce",
            notification_type: "email",
        },
    ]);
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { count: 2 });
    await contains(".o-mail-NotificationItem-counter", { count: 2, text: "2" });
});

test("non-failure notifications are ignored", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const messageId = pyEnv["mail.message"].create({
        message_type: "email",
        model: "res.partner",
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "ready",
        notification_type: "email",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { count: 0 });
});

test("marked as read thread notifications are ordered by last message date", async () => {
    const pyEnv = await startServer();
    const [channelId_1, channelId_2] = pyEnv["discuss.channel"].create([
        { name: "Channel 2019" },
        { name: "Channel 2020" },
    ]);
    pyEnv["mail.message"].create([
        {
            body: "not empty",
            date: "2019-01-01 00:00:00",
            model: "discuss.channel",
            res_id: channelId_1,
        },
        {
            body: "not empty",
            date: "2020-01-01 00:00:00",
            model: "discuss.channel",
            res_id: channelId_2,
        },
    ]);
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { count: 2 });
    await contains(":nth-child(1 of .o-mail-NotificationItem)", { text: "Channel 2020" });
    await contains(":nth-child(2 of .o-mail-NotificationItem)", { text: "Channel 2019" });
});

test("thread notifications are re-ordered on receiving a new message", async () => {
    const pyEnv = await startServer();
    const [channelId_1, channelId_2] = pyEnv["discuss.channel"].create([
        { name: "Channel 2019" },
        { name: "Channel 2020" },
    ]);
    pyEnv["mail.message"].create([
        {
            date: "2019-01-01 00:00:00",
            model: "discuss.channel",
            res_id: channelId_1,
        },
        {
            date: "2020-01-01 00:00:00",
            model: "discuss.channel",
            res_id: channelId_2,
        },
    ]);
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { count: 2 });
    const channel_1 = pyEnv["discuss.channel"].search_read([["id", "=", channelId_1]])[0];
    pyEnv["bus.bus"]._sendone(channel_1, "discuss.channel/new_message", {
        id: channelId_1,
        message: {
            author: { id: 7, name: "Demo User" },
            body: "<p>New message !</p>",
            date: "2020-03-23 10:00:00",
            id: 44,
            message_type: "comment",
            model: "discuss.channel",
            record_name: "Channel 2019",
            res_id: channelId_1,
        },
    });
    await contains(":nth-child(1 of .o-mail-NotificationItem)", { text: "Channel 2019" });
    await contains(":nth-child(2 of .o-mail-NotificationItem)", { text: "Channel 2020" });
    await contains(".o-mail-NotificationItem", { count: 2 });
});

test("messaging menu counter should ignore unread messages in channels that are unpinned", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["discuss.channel"].create({ name: "General" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                unpin_dt: "2023-01-01 12:00:00",
                last_interest_dt: "2023-01-01 11:00:00",
                message_unread_counter: 1,
                partner_id: serverState.partnerId,
            }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    pyEnv["mail.message"].create([
        {
            model: "discuss.channel",
            res_id: channelId,
            author_id: partnerId,
            message_type: "email",
        },
    ]);
    await start();
    await contains(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu-counter", { count: 0 });
    await click(".o_menu_systray i[aria-label='Messages']"); // fetch channels
    await contains(".o-mail-NotificationItem", { text: "General" }); // ensure channels fetched
    await contains(".o-mail-MessagingMenu-counter", { count: 0 });
});
