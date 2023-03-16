/** @odoo-module **/

import { start, startServer, click } from "@mail/../tests/helpers/test_utils";
import { patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module("sms message menu");

QUnit.test("mark as read", async (assert) => {
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
    assert.containsOnce($, ".o-mail-NotificationItem");
    assert.containsOnce($, ".o-mail-NotificationItem i[title='Mark As Read']");
    assert.containsOnce(
        $,
        ".o-mail-NotificationItem:contains(An error occurred when sending an SMS)"
    );
    await click(".o-mail-NotificationItem i[title='Mark As Read']");
    assert.containsNone($, ".o-mail-NotificationItem");
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
    assert.containsN($, ".o-mail-NotificationItem", 2);
    const items = $(".o-mail-NotificationItem");
    assert.ok(items[0].textContent.includes("Partner (2)"));
    assert.ok(items[0].textContent.includes("An error occurred when sending an email"));
    assert.ok(items[1].textContent.includes("Partner (2)"));
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
    assert.containsOnce($, ".o-mail-NotificationItem");
    assert.containsOnce($, ".o-mail-NotificationItem:contains(Partner (2))");
    await click(".o-mail-NotificationItem");
    assert.verifySteps(["do_action"]);
});
