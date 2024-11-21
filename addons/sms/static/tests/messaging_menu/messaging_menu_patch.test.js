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
import { defineSMSModels } from "@sms/../tests/sms_test_helpers";
import { mockService, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineSMSModels();

test("mark as read", async () => {
    const pyEnv = await startServer();
    const messageId = pyEnv["mail.message"].create({
        message_type: "sms",
        model: "res.partner",
        res_id: serverState.partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "exception",
        notification_type: "sms",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem");
    await triggerEvents(".o-mail-NotificationItem", ["mouseenter"], { text: "" });
    await contains(".o-mail-NotificationItem [title='Mark As Read']");
    await contains(".o-mail-NotificationItem-text", {
        text: "An error occurred when sending an SMS",
    });
    await click(".o-mail-NotificationItem [title='Mark As Read']");
    await contains(".o-mail-NotificationItem", { count: 0 });
});

test("notifications grouped by notification_type", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            message_type: "sms",
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
            notification_type: "sms",
        },
        {
            mail_message_id: messageId_1,
            notification_status: "exception",
            notification_type: "sms",
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
            [".o-mail-NotificationItem-name", { text: "Contact" }],
            [".o-mail-NotificationItem-counter", { text: "2" }],
            [".o-mail-NotificationItem-text", { text: "An error occurred when sending an email" }],
        ],
    });
    await contains(":nth-child(2 of .o-mail-NotificationItem)", {
        contains: [
            [".o-mail-NotificationItem-name", { text: "Contact" }],
            [".o-mail-NotificationItem-counter", { text: "2" }],
            [".o-mail-NotificationItem-text", { text: "An error occurred when sending an SMS" }],
        ],
    });
});

test("grouped notifications by document model", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2 ]= pyEnv["res.partner"].create([{}, {}]);
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            message_type: "sms",
            model: "res.partner",
            res_id: partnerId_1,
        },
        {
            message_type: "sms",
            model: "res.partner",
            res_id: partnerId_2,
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId_1,
            notification_status: "exception",
            notification_type: "sms",
        },
        {
            mail_message_id: messageId_2,
            notification_status: "exception",
            notification_type: "sms",
        },
    ]);
    mockService("action", {
        doAction(action) {
            step("do_action");
            expect(action.name).toBe("SMS Failures");
            expect(action.type).toBe("ir.actions.act_window");
            expect(action.view_mode).toBe("kanban,list,form");
            expect(action.views).toEqual([[false, "kanban"],[false, "list"],[false, "form"]]);
            expect(action.target).toBe("current");
            expect(action.res_model).toBe("res.partner");
            expect(action.domain).toEqual([["message_has_sms_error", "=", true]]);
        },
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", {
        text: "Contact",
        contains: [".badge", { text: "2" }],
    });
    await assertSteps(["do_action"]);
});
