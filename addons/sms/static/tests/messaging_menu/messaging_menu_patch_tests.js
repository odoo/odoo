/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { patchWithCleanup, triggerEvent } from "@web/../tests/helpers/utils";
import { click, contains } from "@web/../tests/utils";

QUnit.module("messaging menu (patch)");

QUnit.test("mark as read", async () => {
    const pyEnv = await startServer();
    const messageId = pyEnv["mail.message"].create({
        message_type: "sms",
        model: "res.partner",
        res_id: pyEnv.currentPartnerId,
        res_model_name: "Partner",
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "exception",
        notification_type: "sms",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem");
    await triggerEvent($(".o-mail-NotificationItem")[0], null, "mouseenter");
    await contains(".o-mail-NotificationItem [title='Mark As Read']");
    await contains(".o-mail-NotificationItem-text", {
        text: "An error occurred when sending an SMS",
    });
    await click(".o-mail-NotificationItem [title='Mark As Read']");
    await contains(".o-mail-NotificationItem", { count: 0 });
});

QUnit.test("notifications grouped by notification_type", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            message_type: "sms",
            model: "res.partner",
            res_id: partnerId,
            res_model_name: "Partner",
        },
        {
            message_type: "email",
            model: "res.partner",
            res_id: partnerId,
            res_model_name: "Partner",
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
    const items = $(".o-mail-NotificationItem");
    assert.ok(items[0].textContent.includes("Partner"));
    assert.ok(items[0].textContent.includes("2")); // counter
    assert.ok(items[0].textContent.includes("An error occurred when sending an email"));
    assert.ok(items[1].textContent.includes("Partner"));
    assert.ok(items[1].textContent.includes("2")); // counter
    assert.ok(items[1].textContent.includes("An error occurred when sending an SMS"));
});

QUnit.test("grouped notifications by document model", async (assert) => {
    const pyEnv = await startServer();
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            message_type: "sms",
            model: "res.partner",
            res_id: 31,
            res_model_name: "Partner",
        },
        {
            message_type: "sms",
            model: "res.partner",
            res_id: 32,
            res_model_name: "Partner",
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
    const { env } = await start();
    patchWithCleanup(env.services.action, {
        doAction(action) {
            assert.step("do_action");
            assert.strictEqual(action.name, "SMS Failures");
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
                JSON.stringify([["message_has_sms_error", "=", true]])
            );
        },
    });

    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", {
        text: "Partner",
        contains: [".badge", { text: "2" }],
    });
    assert.verifySteps(["do_action"]);
});
