/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { serializeDate, today } from "@web/core/l10n/dates";
import {
    mockTimeout,
    patchDate,
    patchWithCleanup,
    triggerHotkey,
} from "@web/../tests/helpers/utils";
import { click, contains, createFile, inputFiles } from "@web/../tests/utils";

const views = {
    "res.fake,false,form": `
        <form string="Fake">
            <sheet></sheet>
            <div class="oe_chatter">
                <field name="activity_ids"/>
                <field name="message_ids"/>
            </div>
        </form>`,
};

QUnit.module("activity");

QUnit.test("activity upload document is available", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const [activityTypeId] = pyEnv["mail.activity.type"].search([["name", "=", "Upload Document"]]);
    pyEnv["mail.activity"].create({
        activity_category: "upload_file",
        activity_type_id: activityTypeId,
        can_write: true,
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity .btn", { text: "Upload Document" });
    await contains(".btn .fa-upload");
    await contains(".o-mail-Activity .o_input_file");
});

QUnit.test("activity can upload a document", async () => {
    const pyEnv = await startServer();
    const fakeId = pyEnv["res.partner"].create({});
    const [activityTypeId] = pyEnv["mail.activity.type"].search([["name", "=", "Upload Document"]]);
    pyEnv["mail.activity"].create({
        activity_category: "upload_file",
        activity_type_id: activityTypeId,
        can_write: true,
        res_id: fakeId,
        res_model: "res.partner",
    });
    const { openFormView } = await start({ serverData: { views } });
    openFormView("res.partner", fakeId);
    await contains(".o-mail-Activity .btn", { text: "Upload Document" });
    await inputFiles(".o-mail-Activity .o_input_file", [
        await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text.txt",
        }),
    ]);
    await contains(".o-mail-Activity .btn", { count: 0, text: "Upload Document" });
    await contains("button[aria-label='Attach files']", { text: "1" });
});

QUnit.test("activity simplest layout", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity");
    await contains(".o-mail-Activity-sidebar");
    await contains(".o-mail-Activity-user");
    await contains(".o-mail-Activity-note", { count: 0 });
    await contains(".o-mail-Activity-details", { count: 0 });
    await contains(".o-mail-Activity-mailTemplates", { count: 0 });
    await contains(".btn", { count: 0, text: "Edit" });
    await contains(".o-mail-Activity .btn", { count: 0, text: "Cancel" });
    await contains(".btn", { count: 0, text: "Mark Done" });
    await contains(".o-mail-Activity .btn", { count: 0, text: "Upload Document" });
});

QUnit.test("activity with note layout", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        note: "<p>There is no good or bad note</p>",
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity");
    await contains(".o-mail-Activity-note", { text: "There is no good or bad note" });
});

QUnit.test("activity info layout when planned after tomorrow", async () => {
    patchDate(2023, 0, 11, 12, 0, 0);
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        date_deadline: serializeDate(today().plus({ days: 5 })),
        res_id: partnerId,
        res_model: "res.partner",
        state: "planned",
    });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity span.text-success", { text: "Due in 5 days:" });
});

QUnit.test("activity info layout when planned tomorrow", async () => {
    patchDate(2023, 0, 11, 12, 0, 0);
    const tomorrow = today().plus({ days: 1 });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        date_deadline: serializeDate(tomorrow),
        res_id: partnerId,
        res_model: "res.partner",
        state: "planned",
    });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity span.text-success", { text: "Tomorrow:" });
});

QUnit.test("activity info layout when planned today", async () => {
    patchDate(2023, 0, 11, 12, 0, 0);
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        date_deadline: serializeDate(today()),
        res_id: partnerId,
        res_model: "res.partner",
        state: "today",
    });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity span.text-warning", { text: "Today:" });
});

QUnit.test("activity info layout when planned yesterday", async () => {
    patchDate(2023, 0, 11, 12, 0, 0);
    const yesterday = today().plus({ days: -1 });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        date_deadline: serializeDate(yesterday),
        res_id: partnerId,
        res_model: "res.partner",
        state: "overdue",
    });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity span.text-danger", { text: "Yesterday:" });
});

QUnit.test("activity info layout when planned before yesterday", async () => {
    patchDate(2023, 0, 11, 12, 0, 0);
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        date_deadline: serializeDate(today().plus({ days: -5 })),
        res_id: partnerId,
        res_model: "res.partner",
        state: "overdue",
    });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity span.text-danger", { text: "5 days overdue:" });
});

/**
 * Test if the activity layout change while crossing a day.
 * Pass locally or if triggered on runbot manually, but fail on ci build.
 * The hook/runbot environment might not support this test, so skipped for now.
 */
QUnit.skip("activity info layout change at midnight", async () => {
    const mock = mockTimeout();
    patchDate(2023, 11, 7, 23, 59, 59);
    const tomorrow = today().plus({ days: 1 });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        date_deadline: serializeDate(tomorrow),
        res_id: partnerId,
        res_model: "res.partner",
        state: "planned",
    });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity span.text-success", { text: "Tomorrow:" });

    patchDate(2023, 11, 8, 0, 0, 1); // OXP is coming!
    await mock.advanceTime(2000);
    await contains(".o-mail-Activity span.text-warning", { text: "Today:" });
});

QUnit.test("activity with a summary layout", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        res_id: partnerId,
        res_model: "res.partner",
        summary: "test summary",
    });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity", { text: "“test summary”" });
});

QUnit.test("activity without summary layout", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        activity_type_id: 1,
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity", { text: "Email" });
});

QUnit.test("activity details toggle", async () => {
    patchDate(2023, 0, 11, 12, 0, 0);
    const tomorrow = today().plus({ days: 1 });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["mail.activity"].create({
        create_date: serializeDate(today()),
        create_uid: userId,
        date_deadline: serializeDate(tomorrow),
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity");
    await contains(".o-mail-Activity-details", { count: 0 });
    await contains(".o-mail-Activity i[aria-label='Info']");

    await click(".o-mail-Activity i[aria-label='Info']");
    await contains(".o-mail-Activity-details");

    await click(".o-mail-Activity i[aria-label='Info']");
    await contains(".o-mail-Activity-details", { count: 0 });
});

QUnit.test("activity with mail template layout", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const mailTemplateId = pyEnv["mail.template"].create({ name: "Dummy mail template" });
    const activityTypeId = pyEnv["mail.activity.type"].search([["name", "=", "Email"]])[0];
    pyEnv["mail.activity"].create({
        activity_type_id: activityTypeId,
        mail_template_ids: [mailTemplateId],
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity");
    await contains(".o-mail-Activity-sidebar");
    await contains(".o-mail-Activity-mailTemplates");
    await contains(".o-mail-ActivityMailTemplate-name", { text: "Dummy mail template" });
    await contains(".o-mail-ActivityMailTemplate-preview");
    await contains(".o-mail-ActivityMailTemplate-send");
});

QUnit.test("activity with mail template: preview mail", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const mailTemplateId = pyEnv["mail.template"].create({ name: "Dummy mail template" });
    const activityTypeId = pyEnv["mail.activity.type"].search([["name", "=", "Email"]])[0];
    pyEnv["mail.activity"].create({
        activity_type_id: activityTypeId,
        mail_template_ids: [mailTemplateId],
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { env, openFormView } = await start();
    openFormView("res.partner", partnerId);
    patchWithCleanup(env.services.action, {
        doAction(action) {
            assert.step("do_action");
            assert.deepEqual(action.context.default_res_ids, [partnerId]);
            assert.strictEqual(action.context.default_model, "res.partner");
            assert.strictEqual(action.context.default_template_id, mailTemplateId);
            assert.strictEqual(action.type, "ir.actions.act_window");
            assert.strictEqual(action.res_model, "mail.compose.message");
        },
    });
    await contains(".o-mail-Activity");
    await contains(".o-mail-ActivityMailTemplate-preview");

    await click(".o-mail-ActivityMailTemplate-preview");
    assert.verifySteps(["do_action"]);
});

QUnit.test("activity with mail template: send mail", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const mailTemplateId = pyEnv["mail.template"].create({ name: "Dummy mail template" });
    const activityTypeId = pyEnv["mail.activity.type"].search([["name", "=", "Email"]])[0];
    pyEnv["mail.activity"].create({
        activity_type_id: activityTypeId,
        mail_template_ids: [mailTemplateId],
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { openFormView } = await start({
        async mockRPC(route, args) {
            if (args.method === "activity_send_mail") {
                assert.step("activity_send_mail");
                assert.strictEqual(args.args[0].length, 1);
                assert.strictEqual(args.args[0][0], partnerId);
                assert.strictEqual(args.args[1], mailTemplateId);
                // random value returned in order for the mock server to know that this route is implemented.
                return true;
            }
        },
    });
    openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity");
    await contains(".o-mail-ActivityMailTemplate-send");

    await click(".o-mail-ActivityMailTemplate-send");
    assert.verifySteps(["activity_send_mail"]);
});

QUnit.test("activity click on mark as done", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const activityTypeId = pyEnv["mail.activity.type"].search([["name", "=", "Email"]])[0];
    pyEnv["mail.activity"].create({
        activity_category: "default",
        activity_type_id: activityTypeId,
        can_write: true,
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity");
    await click(".btn", { text: "Mark Done" });
    await contains(".o-mail-ActivityMarkAsDone");
    await click(".btn", { text: "Mark Done" });
    await contains(".o-mail-ActivityMarkAsDone", { count: 0 });
});

QUnit.test(
    "activity mark as done popover should focus feedback input on open [REQUIRE FOCUS]",
    async () => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({});
        const activityTypeId = pyEnv["mail.activity.type"].search([["name", "=", "Email"]])[0];
        pyEnv["mail.activity"].create({
            activity_category: "default",
            activity_type_id: activityTypeId,
            can_write: true,
            res_id: partnerId,
            res_model: "res.partner",
        });
        const { openFormView } = await start();
        openFormView("res.partner", partnerId);
        await contains(".o-mail-Activity");
        await click(".btn", { text: "Mark Done" });
        await contains(".o-mail-ActivityMarkAsDone textarea[placeholder='Write Feedback']:focus");
    }
);

QUnit.test("activity click on edit", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const mailTemplateId = pyEnv["mail.template"].create({ name: "Dummy mail template" });
    const activityTypeId = pyEnv["mail.activity.type"].search([["name", "=", "Email"]])[0];
    const activityId = pyEnv["mail.activity"].create({
        activity_type_id: activityTypeId,
        can_write: true,
        mail_template_ids: [mailTemplateId],
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { env, openFormView } = await start();
    openFormView("res.partner", partnerId);
    patchWithCleanup(env.services.action, {
        doAction(action) {
            assert.step("do_action");
            assert.strictEqual(action.type, "ir.actions.act_window");
            assert.strictEqual(action.res_model, "mail.activity");
            assert.strictEqual(action.res_id, activityId);
            return super.doAction(...arguments);
        },
    });
    await click(".o-mail-Activity .btn", { text: "Edit" });
    assert.verifySteps(["do_action"]);
});

QUnit.test("activity click on cancel", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const activityTypeId = pyEnv["mail.activity.type"].search([["name", "=", "Email"]])[0];
    const activityId = pyEnv["mail.activity"].create({
        activity_type_id: activityTypeId,
        can_write: true,
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { openFormView } = await start({
        async mockRPC(route, args) {
            if (route === "/web/dataset/call_kw/mail.activity/unlink") {
                assert.step("unlink");
                assert.strictEqual(args.args[0].length, 1);
                assert.strictEqual(args.args[0][0], activityId);
            }
        },
    });
    openFormView("res.partner", partnerId);
    await click(".o-mail-Activity .btn", { text: "Cancel" });
    await contains(".o-mail-Activity", { count: 0 });
    assert.verifySteps(["unlink"]);
});

QUnit.test("activity mark done popover close on ESCAPE", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const activityTypeId = pyEnv["mail.activity.type"].search([["name", "=", "Email"]])[0];
    pyEnv["mail.activity"].create({
        activity_category: "default",
        activity_type_id: activityTypeId,
        can_write: true,
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);

    await click(".btn", { text: "Mark Done" });
    await contains(".o-mail-ActivityMarkAsDone");

    triggerHotkey("Escape");
    await contains(".o-mail-ActivityMarkAsDone", { count: 0 });
});

QUnit.test("activity mark done popover click on discard", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const activityTypeId = pyEnv["mail.activity.type"].search([["name", "=", "Email"]])[0];
    pyEnv["mail.activity"].create({
        activity_category: "default",
        activity_type_id: activityTypeId,
        can_write: true,
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);
    await click(".btn", { text: "Mark Done" });
    await click(".o-mail-ActivityMarkAsDone button", { text: "Discard" });
    await contains(".o-mail-ActivityMarkAsDone", { count: 0 });
});

QUnit.test("Activity are sorted by deadline", async () => {
    patchDate(2023, 0, 11, 12, 0, 0);
    const dateBefore = today().plus({ days: -5 });
    const dateAfter = today().plus({ days: 4 });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        date_deadline: serializeDate(dateAfter),
        res_id: partnerId,
        res_model: "res.partner",
        state: "planned",
    });
    pyEnv["mail.activity"].create({
        date_deadline: serializeDate(today()),
        res_id: partnerId,
        res_model: "res.partner",
        state: "today",
    });
    pyEnv["mail.activity"].create({
        date_deadline: serializeDate(dateBefore),
        res_id: partnerId,
        res_model: "res.partner",
        state: "overdue",
    });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);
    await contains(":nth-child(1 of .o-mail-Activity)", { text: "5 days overdue:" });
    await contains(":nth-child(2 of .o-mail-Activity)", { text: "Today:" });
    await contains(":nth-child(3 of .o-mail-Activity)", { text: "Due in 4 days:" });
});

QUnit.test("chatter 'activities' button open the activity schedule wizard", async (assert) => {
    const pyEnv = await startServer();
    const fakeId = pyEnv["res.partner"].create({});
    const { env, openFormView } = await start({ serverData: { views } });
    await openFormView("res.partner", fakeId);
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            assert.step("doAction");
            var expectedAction = {
                context: {
                    active_ids: [fakeId],
                    active_id: fakeId,
                    active_model: "res.partner",
                },
                name: "Schedule Activity",
                res_model: "mail.activity.schedule",
                target: "new",
                type: "ir.actions.act_window",
                view_mode: "form",
                views: [[false, "form"]],
            };
            assert.deepEqual(
                action,
                expectedAction,
                "should execute an action with correct params"
            );
            options.onClose();
            return Promise.resolve();
        },
    });
    await click("button", { text: "Activities" });
    assert.verifySteps(["doAction"]);
});
