/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { patchWithCleanup, triggerEvent } from "@web/../tests/helpers/utils";
import { click, contains } from "@web/../tests/utils";

QUnit.module("messaging menu (patch)");

QUnit.test("mark as read", async () => {
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
    await contains(".o-mail-NotificationItem");
    await triggerEvent($(".o-mail-NotificationItem")[0], null, "mouseenter");
    await contains(".o-mail-NotificationItem-text", {
        text: "An error occurred when sending a letter with Snailmail.",
    });
    await click(".o-mail-NotificationItem [title='Mark As Read']");
    await contains(".o-mail-NotificationItem", { count: 0 });
});

QUnit.test("notifications grouped by notification_type", async () => {
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
    await contains(".o-mail-NotificationItem", { count: 2 });
    await contains(":nth-child(1 of .o-mail-NotificationItem)", {
        contains: [
            [".o-mail-NotificationItem-name", { text: "Partner" }],
            [".o-mail-NotificationItem-counter", { text: "2" }],
            [".o-mail-NotificationItem-text", { text: "An error occurred when sending an email" }],
        ],
    });
    await contains(":nth-child(2 of .o-mail-NotificationItem)", {
        contains: [
            [".o-mail-NotificationItem-name", { text: "Partner" }],
            [".o-mail-NotificationItem-counter", { text: "2" }],
            [
                ".o-mail-NotificationItem-text",
                { text: "An error occurred when sending a letter with Snailmail." },
            ],
        ],
    });
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
    await contains(".o-mail-NotificationItem", { text: "Partner" });
    await contains(".o-mail-NotificationItem-counter", { text: "2" });
    await click(".o-mail-NotificationItem");
    assert.verifySteps(["do_action"]);
});
