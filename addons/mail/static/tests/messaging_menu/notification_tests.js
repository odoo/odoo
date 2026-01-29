/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";

import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { click, contains, triggerEvents } from "@web/../tests/utils";

QUnit.module("notification");

QUnit.test("basic layout", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    const messageId = pyEnv["mail.message"].create({
        message_type: "email",
        model: "discuss.channel",
        res_id: channelId,
        res_model_name: "Channel",
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
            [".o-mail-NotificationItem-name", { text: "Channel" }],
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

QUnit.test("mark as read", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    const messageId = pyEnv["mail.message"].create({
        message_type: "email",
        model: "discuss.channel",
        res_id: channelId,
        res_model_name: "Channel",
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "exception",
        notification_type: "email",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await triggerEvents(".o-mail-NotificationItem", ["mouseenter"], { text: "Channel" });
    await click(".o-mail-NotificationItem-markAsRead", {
        parent: [".o-mail-NotificationItem", { text: "Channel" }],
    });
    await contains(".o-mail-NotificationItem", { count: 0, text: "Channel" });
});

QUnit.test("open non-channel failure", async (assert) => {
    const pyEnv = await startServer();
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            message_type: "email",
            model: "res.partner",
            res_id: 31,
            res_model_name: "Partner",
        },
        {
            message_type: "email",
            model: "res.partner",
            res_id: 32,
            res_model_name: "Partner",
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

    const { env } = await start();
    patchWithCleanup(env.services.action, {
        doAction(action) {
            assert.step("do_action");
            assert.strictEqual(action.name, "Mail Failures");
            assert.strictEqual(action.type, "ir.actions.act_window");
            assert.strictEqual(action.view_mode, "kanban,list,form");
            assert.strictEqual(
                JSON.stringify(action.views),
                JSON.stringify([
                    [false, "kanban"],
                    [false, "list"],
                    [false, "form"],
                ])
            );
            assert.strictEqual(action.target, "current");
            assert.strictEqual(action.res_model, "res.partner");
            assert.strictEqual(
                JSON.stringify(action.domain),
                JSON.stringify([["message_has_error", "=", true]])
            );
        },
    });
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    assert.verifySteps(["do_action"]);
});

QUnit.test("different discuss.channel are not grouped", async () => {
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
            res_model_name: "Channel",
        },
        {
            message_type: "email",
            model: "discuss.channel",
            res_id: channelId_2,
            res_model_name: "Channel",
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

QUnit.test("multiple grouped notifications by model", async () => {
    const pyEnv = await startServer();
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            message_type: "email",
            model: "res.partner",
            res_id: 31,
            res_model_name: "Partner",
        },
        {
            message_type: "email",
            model: "res.company",
            res_id: 32,
            res_model_name: "Company",
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

QUnit.test("non-failure notifications are ignored", async () => {
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

QUnit.test("marked as read thread notifications are ordered by last message date", async () => {
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

QUnit.test("thread notifications are re-ordered on receiving a new message", async () => {
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
    const channel_1 = pyEnv["discuss.channel"].searchRead([["id", "=", channelId_1]])[0];
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

QUnit.test(
    "messaging menu counter should ignore unread messages in channels that are unpinned",
    async () => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({});
        const channelId = pyEnv["discuss.channel"].create({
            channel_member_ids: [
                Command.create({
                    is_pinned: false,
                    message_unread_counter: 1,
                    partner_id: pyEnv.currentPartnerId,
                }),
                Command.create({ partner_id: partnerId }),
            ],
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
    }
);

QUnit.test(
    "subtype description should be displayed when body is empty",
    async () => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Partner1" });
        const channelId = pyEnv["discuss.channel"].create({ name: "Test" });
        const subtypeId = pyEnv["mail.message.subtype"].create({ description: "hello" });
        pyEnv["mail.message"].create({
            author_id: partnerId,
            body: "",
            model: "discuss.channel",
            res_id: channelId,
            subtype_id: subtypeId,
        });
        await start();
        await click(".o_menu_systray i[aria-label='Messages']");
        await contains(".o-mail-NotificationItem-text", { text: "Partner1: hello" });
    }
);
