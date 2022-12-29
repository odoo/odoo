/** @odoo-module **/

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";
import { getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";

let target;

QUnit.module("messaging menu", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("should have messaging menu button in systray", async (assert) => {
    await start();
    assert.containsOnce(target, ".o_menu_systray i[aria-label='Messages']");
    assert.containsNone(target, ".o-mail-messaging-menu", "messaging menu closed by default");
    assert.hasClass(
        target.querySelector(".o_menu_systray i[aria-label='Messages']"),
        "fa-comments"
    );
});

QUnit.test("messaging menu should have topbar buttons", async function (assert) {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsOnce(target, ".o-mail-messaging-menu");
    assert.containsN(target, ".o-mail-messaging-menu-topbar button", 4);
    assert.containsOnce(target, ".o-mail-messaging-menu-topbar button:contains(All)");
    assert.containsOnce(target, ".o-mail-messaging-menu-topbar button:contains(Chat)");
    assert.containsOnce(target, ".o-mail-messaging-menu-topbar button:contains(Channels)");
    assert.containsOnce(target, ".o-mail-messaging-menu-topbar button:contains(New Message)");
    assert.hasClass(
        $(target).find(".o-mail-messaging-menu-topbar button:contains(All)"),
        "fw-bolder",
        "'all' tab button should be active"
    );
    assert.doesNotHaveClass(
        $(target).find(".o-mail-messaging-menu-topbar button:contains(Chat)"),
        "fw-bolder"
    );
    assert.doesNotHaveClass(
        $(target).find(".o-mail-messaging-menu-topbar button:contains(Channels)"),
        "fw-bolder"
    );
});

QUnit.test("counter is taking into account failure notification", async function (assert) {
    patchWithCleanup(browser, {
        Notification: {
            ...browser.Notification,
            permission: "denied",
        },
    });
    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv["mail.channel"].create({});
    const mailMessageId1 = pyEnv["mail.message"].create({
        model: "mail.channel",
        res_id: mailChannelId1,
    });
    const [mailChannelMemberId] = pyEnv["mail.channel.member"].search([
        ["channel_id", "=", mailChannelId1],
        ["partner_id", "=", pyEnv.currentPartnerId],
    ]);
    pyEnv["mail.channel.member"].write([mailChannelMemberId], {
        seen_message_id: mailMessageId1,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: mailMessageId1,
        notification_status: "exception",
        notification_type: "email",
    });
    await start();
    assert.containsOnce(target, ".o-mail-messaging-menu-counter");
    assert.strictEqual($(target).find(".o-mail-messaging-menu-counter.badge").text(), "1");
});

QUnit.test("rendering with OdooBot has a request (default)", async function (assert) {
    patchWithCleanup(browser, {
        Notification: {
            ...browser.Notification,
            permission: "default",
        },
    });
    await start();
    assert.containsOnce(target, ".o-mail-messaging-menu-counter");
    assert.strictEqual($(target).find(".o-mail-messaging-menu-counter").text(), "1");
});

QUnit.test("rendering without OdooBot has a request (denied)", async function (assert) {
    patchWithCleanup(browser, {
        Notification: {
            permission: "denied",
        },
    });
    await start();
    assert.strictEqual($(target).find(".o-mail-messaging-menu-counter").text(), "0");
});

QUnit.test("rendering without OdooBot has a request (accepted)", async function (assert) {
    patchWithCleanup(browser, {
        Notification: {
            permission: "granted",
        },
    });
    await start();
    assert.strictEqual($(target).find(".o-mail-messaging-menu-counter").text(), "0");
});

QUnit.test("Is closed after clicking on new message", async function (assert) {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-messaging-menu-new-message");
    assert.containsNone(target, ".o-mail-messaging-menu");
});

QUnit.test("no 'New Message' button when discuss is open", async function (assert) {
    const { openDiscuss, openView } = await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsOnce(target, ".o-mail-messaging-menu-topbar button:contains(New Message)");

    await openDiscuss();
    assert.containsNone(target, ".o-mail-messaging-menu-topbar button:contains(New Message)");

    await openView({
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce(target, ".o-mail-messaging-menu-topbar button:contains(New Message)");

    await openDiscuss();
    assert.containsNone(target, ".o-mail-messaging-menu-topbar button:contains(New Message)");
});

QUnit.test("grouped notifications by document", async function (assert) {
    const pyEnv = await startServer();
    const [mailMessageId1, mailMessageId2] = pyEnv["mail.message"].create([
        {
            message_type: "email",
            model: "res.partner",
            res_id: 31,
            res_model_name: "Partner",
        },
        {
            message_type: "email",
            model: "res.partner",
            res_id: 31,
            res_model_name: "Partner",
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: mailMessageId1,
            notification_status: "exception",
            notification_type: "email",
        },
        {
            mail_message_id: mailMessageId2,
            notification_status: "bounce",
            notification_type: "email",
        },
    ]);
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsOnce(target, ".o-mail-notification-item");
    assert.containsOnce(target, ".o-mail-notification-item:contains(Partner (2))");
    assert.containsNone(target, ".o-mail-chat-window");

    await click(".o-mail-notification-item");
    assert.containsOnce(target, ".o-mail-chat-window");
});

QUnit.test("grouped notifications by document model", async function (assert) {
    const pyEnv = await startServer();
    const [mailMessageId1, mailMessageId2] = pyEnv["mail.message"].create([
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
            mail_message_id: mailMessageId1,
            notification_status: "exception",
            notification_type: "email",
        },
        {
            mail_message_id: mailMessageId2,
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
    assert.containsOnce(target, ".o-mail-notification-item:contains(Partner (2))");

    document.querySelector(".o-mail-notification-item").click();
    assert.verifySteps(["do_action"]);
});

QUnit.test(
    "multiple grouped notifications by document model, sorted by the most recent message of each group",
    async function (assert) {
        const pyEnv = await startServer();
        const [mailMessageId1, mailMessageId2] = pyEnv["mail.message"].create([
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
                mail_message_id: mailMessageId1,
                notification_status: "exception",
                notification_type: "email",
            },
            {
                mail_message_id: mailMessageId1,
                notification_status: "exception",
                notification_type: "email",
            },
            {
                mail_message_id: mailMessageId2,
                notification_status: "bounce",
                notification_type: "email",
            },
            {
                mail_message_id: mailMessageId2,
                notification_status: "bounce",
                notification_type: "email",
            },
        ]);
        await start();
        await click(".o_menu_systray i[aria-label='Messages']");
        assert.containsN(target, ".o-mail-notification-item", 2);
        const items = target.querySelectorAll(".o-mail-notification-item");
        assert.ok(items[0].textContent.includes("Company"));
        assert.ok(items[1].textContent.includes("Partner"));
    }
);

QUnit.test("non-failure notifications are ignored", async function (assert) {
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({});
    const mailMessageId1 = pyEnv["mail.message"].create({
        message_type: "email",
        model: "res.partner",
        res_id: resPartnerId1,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: mailMessageId1,
        notification_status: "ready",
        notification_type: "email",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsNone(target, ".o-mail-notification-item");
});

QUnit.test("mark unread channel as read", async function (assert) {
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({ name: "Demo" });
    const mailChannelId1 = pyEnv["mail.channel"].create({
        channel_member_ids: [
            [
                0,
                0,
                {
                    message_unread_counter: 1,
                    partner_id: pyEnv.currentPartnerId,
                },
            ],
            [
                0,
                0,
                {
                    partner_id: resPartnerId1,
                },
            ],
        ],
    });
    const [mailMessageId1] = pyEnv["mail.message"].create([
        { author_id: resPartnerId1, model: "mail.channel", res_id: mailChannelId1 },
        { author_id: resPartnerId1, model: "mail.channel", res_id: mailChannelId1 },
    ]);
    const [mailChannelMemberId] = pyEnv["mail.channel.member"].search([
        ["channel_id", "=", mailChannelId1],
        ["partner_id", "=", pyEnv.currentPartnerId],
    ]);
    pyEnv["mail.channel.member"].write([mailChannelMemberId], {
        seen_message_id: mailMessageId1,
    });
    await start({
        async mockRPC(route, args) {
            if (route.includes("set_last_seen_message")) {
                assert.step("set_last_seen_message");
            }
        },
    });
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsOnce(target, ".o-mail-notification-item i[title='Mark As Read']");

    await click(".o-mail-notification-item i[title='Mark As Read']");
    assert.verifySteps(["set_last_seen_message"]);
    assert.hasClass(target.querySelector(".o-mail-notification-item"), "o-muted");
    assert.containsNone(target, ".o-mail-notification-item i[title='Mark As Read']");
    assert.containsNone(target, ".o-mail-chat-window");
});

QUnit.test("mark failure as read", async function (assert) {
    const pyEnv = await startServer();
    const mailMessageId1 = pyEnv["mail.message"].create({
        message_type: "email",
        res_model_name: "Channel",
    });
    pyEnv["mail.channel"].create({
        message_ids: [mailMessageId1],
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId, seen_message_id: mailMessageId1 }],
        ],
    });
    pyEnv["mail.notification"].create({
        mail_message_id: mailMessageId1,
        notification_status: "exception",
        notification_type: "email",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsOnce(target, ".o-mail-notification-item:contains(Channel)");
    assert.containsOnce(
        target,
        ".o-mail-notification-item:contains(An error occurred when sending an email)"
    );
    assert.containsOnce(
        target,
        ".o-mail-notification-item:contains(Channel) i[title='Mark As Read']"
    );

    await click(".o-mail-notification-item i[title='Mark As Read']");
    assert.containsNone(target, ".o-mail-notification-item:contains(Channel)");
    assert.containsNone(
        target,
        ".o-mail-notification-item:contains(An error occurred when sending an email)"
    );
});

QUnit.test("different mail.channel are not grouped", async function (assert) {
    const pyEnv = await startServer();
    const [mailChannelId1, mailChannelId2] = pyEnv["mail.channel"].create([
        { name: "mailChannel1" },
        { name: "mailChannel2" },
    ]);
    const [mailMessageId1, mailMessageId2] = pyEnv["mail.message"].create([
        {
            message_type: "email",
            model: "mail.channel",
            res_id: mailChannelId1,
            res_model_name: "Channel",
        },
        {
            message_type: "email",
            model: "mail.channel",
            res_id: mailChannelId2,
            res_model_name: "Channel",
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: mailMessageId1,
            notification_status: "exception",
            notification_type: "email",
        },
        {
            mail_message_id: mailMessageId1,
            notification_status: "exception",
            notification_type: "email",
        },
        {
            mail_message_id: mailMessageId2,
            notification_status: "bounce",
            notification_type: "email",
        },
        {
            mail_message_id: mailMessageId2,
            notification_status: "bounce",
            notification_type: "email",
        },
    ]);
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsN(target, ".o-mail-notification-item", 4);

    const group_1 = $(".o-mail-notification-item:contains(Channel (2)):first");
    await click(group_1);
    assert.containsOnce(target, ".o-mail-chat-window");
});
