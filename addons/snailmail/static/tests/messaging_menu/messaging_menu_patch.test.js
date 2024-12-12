import {
    assertSteps,
    click,
    contains,
    start,
    startServer,
    step,
    triggerEvents,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { defineSnailmailModels } from "@snailmail/../tests/snailmail_test_helpers";
import { mockService, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineSnailmailModels();

test("mark as read", async () => {
    const pyEnv = await startServer();
    const messageId = pyEnv["mail.message"].create({
        message_type: "snailmail",
        model: "res.partner",
        res_id: serverState.partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "exception",
        notification_type: "snail",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem");
    await triggerEvents(".o-mail-NotificationItem", ["mouseenter"]);
    await contains(".o-mail-NotificationItem-text", {
        text: "An error occurred when sending a letter with Snailmail on “Mitchell Admin”",
    });
    await click(".o-mail-NotificationItem [title='Mark As Read']");
    await contains(".o-mail-NotificationItem", { count: 0 });
});

test("notifications grouped by notification_type", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            message_type: "snailmail",
            model: "res.partner",
            res_id: partnerId,
        },
        {
            message_type: "email",
            model: "res.partner",
            res_id: partnerId,
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId_1,
            notification_status: "exception",
            notification_type: "snail",
        },
        {
            mail_message_id: messageId_1,
            notification_status: "exception",
            notification_type: "snail",
        },
        {
            mail_message_id: messageId_2,
            notification_status: "exception",
            notification_type: "email",
        },
        {
            mail_message_id: messageId_2,
            notification_status: "exception",
            notification_type: "email",
        },
    ]);
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { count: 2 });
    await contains(":nth-child(1 of .o-mail-NotificationItem)", {
        contains: [
            [".o-mail-NotificationItem-name", { text: "Email Failure: Contact" }],
            [".o-mail-NotificationItem-counter", { text: "2" }],
            [".o-mail-NotificationItem-text", { text: "An error occurred when sending an email" }],
        ],
    });
    await contains(":nth-child(2 of .o-mail-NotificationItem)", {
        contains: [
            [".o-mail-NotificationItem-name", { text: "Snailmail Failure: Contact" }],
            [".o-mail-NotificationItem-counter", { text: "2" }],
            [
                ".o-mail-NotificationItem-text",
                { text: "An error occurred when sending a letter with Snailmail." },
            ],
        ],
    });
});

test("grouped notifications by document model", async (assert) => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([{}, {}]);
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            message_type: "snailmail",
            model: "res.partner",
            res_id: partnerId_1,
        },
        {
            message_type: "snailmail",
            model: "res.partner",
            res_id: partnerId_2,
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId_1,
            notification_status: "exception",
            notification_type: "snail",
        },
        {
            mail_message_id: messageId_2,
            notification_status: "exception",
            notification_type: "snail",
        },
    ]);
    mockService("action", {
        doAction(action) {
            step("do_action");
            expect(action.name).toBe("Snailmail Failures");
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
                JSON.stringify([["message_ids.snailmail_error", "=", true]])
            );
        },
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { text: "Snailmail Failure: Contact" });
    await contains(".o-mail-NotificationItem-counter", { text: "2" });
    await click(".o-mail-NotificationItem");
    assertSteps(["do_action"]);
});
