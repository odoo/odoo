/** @odoo-module **/

import { start, startServer, click } from "@mail/../tests/helpers/test_utils";
import { patchWithCleanup, triggerEvent } from "@web/../tests/helpers/utils";

QUnit.module("messaging menu (patch)");

QUnit.test("mark as read", async (assert) => {
    const pyEnv = await startServer();
    const messageId = pyEnv["mail.message"].create([
        {
            message_type: "snailmail",
            model: "res.partner",
            res_id: pyEnv.currentPartnerId,
            res_model_name: "Partner",
        },
    ]);
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "exception",
        notification_type: "snail",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsOnce($, ".o-mail-NotificationItem");
    await triggerEvent($(".o-mail-NotificationItem")[0], null, "mouseenter");
    assert.containsOnce($, ".o-mail-NotificationItem [title='Mark As Read']");
    assert.containsOnce(
        $,
        ".o-mail-NotificationItem:contains(An error occurred when sending a letter with Snailmail.)"
    );
    await click(".o-mail-NotificationItem [title='Mark As Read']");
    assert.containsNone($, ".o-mail-NotificationItem");
});

QUnit.test("notifications grouped by notification_type", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = await pyEnv["res.partner"].create({});
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            message_type: "snailmail",
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
    assert.containsN($, ".o-mail-NotificationItem", 2);
    assert.ok($(".o-mail-NotificationItem:eq(0)").text().includes("Partner"));
    assert.ok($(".o-mail-NotificationItem:eq(0)").text().includes("2")); // counter
    assert.ok(
        $(".o-mail-NotificationItem:eq(0)")
            .text()
            .includes("An error occurred when sending an email")
    );
    assert.ok($(".o-mail-NotificationItem:eq(1)").text().includes("Partner"));
    assert.ok($(".o-mail-NotificationItem:eq(1)").text().includes("2")); // counter
    assert.ok(
        $(".o-mail-NotificationItem:eq(1)")
            .text()
            .includes("An error occurred when sending a letter with Snailmail.")
    );
});

QUnit.test("grouped notifications by document model", async (assert) => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = await pyEnv["res.partner"].create([{}, {}]);
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            message_type: "snailmail",
            model: "res.partner",
            res_id: partnerId_1,
            res_model_name: "Partner",
        },
        {
            message_type: "snailmail",
            model: "res.partner",
            res_id: partnerId_2,
            res_model_name: "Partner",
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
    const { env } = await start();
    patchWithCleanup(env.services.action, {
        doAction(action) {
            assert.step("do_action");
            assert.strictEqual(action.name, "Snailmail Failures");
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
                JSON.stringify([["message_ids.snailmail_error", "=", true]])
            );
        },
    });
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsOnce($, ".o-mail-NotificationItem");
    assert.containsOnce($, ".o-mail-NotificationItem:contains(Partner)");
    assert.containsOnce($, ".o-mail-NotificationItem:contains(2)"); // counter
    await click(".o-mail-NotificationItem");
    assert.verifySteps(["do_action"]);
});
