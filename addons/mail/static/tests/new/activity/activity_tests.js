/** @odoo-module **/

import { file } from "web.test_utils";
import {
    afterNextRender,
    click,
    start,
    startServer,
    createFile,
    waitUntil,
} from "@mail/../tests/helpers/test_utils";
import {
    patchDate,
    patchWithCleanup,
    triggerHotkey,
    mockTimeout,
} from "@web/../tests/helpers/utils";
import { date_to_str } from "web.time";

const { inputFiles } = file;

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

QUnit.test("activity upload document is available", async (assert) => {
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
    const { openView } = await start();
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-mail-Activity-info:contains('Upload Document')");
    assert.containsOnce($, ".btn .fa-upload");
    assert.containsOnce($, ".o-mail-Activity .o_input_file");
});

QUnit.test("activity can upload a document", async (assert) => {
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
    await openFormView("res.partner", fakeId);
    const file = await createFile({
        content: "hello, world",
        contentType: "text/plain",
        name: "text.txt",
    });
    assert.containsOnce($, ".o-mail-Activity-info:contains('Upload Document')");
    inputFiles($(".o-mail-Activity .o_input_file")[0], [file]);
    await waitUntil(".o-mail-Activity-info:contains('Upload Document')", 0);
    await waitUntil("button[aria-label='Attach files']:contains(1)");
});

QUnit.test("activity simplest layout", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { openView } = await start();
    await openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-mail-Activity");
    assert.containsOnce($, ".o-mail-Activity-sidebar");
    assert.containsOnce($, ".o-mail-Activity-user");
    assert.containsOnce($, ".o-mail-Activity-info");
    assert.containsNone($, ".o-mail-Activity-note");
    assert.containsNone($, ".o-mail-Activity-details");
    assert.containsNone($, ".o-mail-Activity-mailTemplates");
    assert.containsNone($, ".btn:contains('Edit')");
    assert.containsNone($, ".o-mail-Activity span:contains(Cancel)");
    assert.containsNone($, ".btn:contains('Mark Done')");
    assert.containsNone($, ".o-mail-Activity-info:contains('Upload Document')");
});

QUnit.test("activity with note layout", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        note: "<p>There is no good or bad note</p>",
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { openView } = await start();
    await openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-mail-Activity");
    assert.containsOnce($, ".o-mail-Activity-note");
    assert.strictEqual($(".o-mail-Activity-note").text(), "There is no good or bad note");
});

QUnit.test("activity info layout when planned after tomorrow", async (assert) => {
    patchDate(2023, 0, 11, 12, 0, 0);
    const today = new Date();
    const fiveDaysFromNow = new Date();
    fiveDaysFromNow.setDate(today.getDate() + 5);
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        date_deadline: date_to_str(fiveDaysFromNow),
        res_id: partnerId,
        res_model: "res.partner",
        state: "planned",
    });
    const { openView } = await start();
    await openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-mail-Activity");
    assert.containsOnce($, ".o-mail-Activity .text-success");
    assert.containsOnce($, ".o-mail-Activity:contains('Due in 5 days:')");
});

QUnit.test("activity info layout when planned tomorrow", async (assert) => {
    patchDate(2023, 0, 11, 12, 0, 0);
    const today = new Date();
    const tomorrow = new Date();
    tomorrow.setDate(today.getDate() + 1);
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        date_deadline: date_to_str(tomorrow),
        res_id: partnerId,
        res_model: "res.partner",
        state: "planned",
    });
    const { openView } = await start();
    await openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-mail-Activity");
    assert.containsOnce($, ".o-mail-Activity .text-success");
    assert.containsOnce($, ".o-mail-Activity:contains('Tomorrow:')");
});

QUnit.test("activity info layout when planned today", async (assert) => {
    patchDate(2023, 0, 11, 12, 0, 0);
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        date_deadline: date_to_str(new Date()),
        res_id: partnerId,
        res_model: "res.partner",
        state: "today",
    });
    const { openView } = await start();
    await openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-mail-Activity");
    assert.containsOnce($, ".o-mail-Activity .text-warning");
    assert.containsOnce($, ".o-mail-Activity:contains('Today:')");
});

QUnit.test("activity info layout when planned yesterday", async (assert) => {
    patchDate(2023, 0, 11, 12, 0, 0);
    const today = new Date();
    const yesterday = new Date();
    yesterday.setDate(today.getDate() - 1);
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        date_deadline: date_to_str(yesterday),
        res_id: partnerId,
        res_model: "res.partner",
        state: "overdue",
    });
    const { openView } = await start();
    await openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-mail-Activity");
    assert.containsOnce($, ".o-mail-Activity .text-danger");
    assert.containsOnce($, ".o-mail-Activity:contains('Yesterday:')");
});

QUnit.test("activity info layout when planned before yesterday", async (assert) => {
    patchDate(2023, 0, 11, 12, 0, 0);
    const today = new Date();
    const fiveDaysBeforeNow = new Date();
    fiveDaysBeforeNow.setDate(today.getDate() - 5);
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        date_deadline: date_to_str(fiveDaysBeforeNow),
        res_id: partnerId,
        res_model: "res.partner",
        state: "overdue",
    });
    const { openView } = await start();
    await openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-mail-Activity");
    assert.containsOnce($, ".o-mail-Activity .text-danger");
    assert.containsOnce($, ".o-mail-Activity:contains('5 days overdue:')");
});

/**
 * Test if the activity layout change while crossing a day.
 * Pass locally or if triggered on runbot manually, but fail on ci build.
 * The hook/runbot environment might not support this test, so skipped for now.
 */
QUnit.skip("activity info layout change at midnight", async (assert) => {
    const mock = mockTimeout();
    patchDate(2023, 11, 7, 23, 59, 59);
    const today = new Date();
    const tomorrow = new Date();
    tomorrow.setDate(today.getDate() + 1);
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        date_deadline: date_to_str(tomorrow),
        res_id: partnerId,
        res_model: "res.partner",
        state: "planned",
    });
    const { openView } = await start();
    await openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-mail-Activity");
    assert.containsOnce($, ".o-mail-Activity .text-success");
    assert.containsOnce($, ".o-mail-Activity:contains('Tomorrow:')");

    patchDate(2023, 11, 8, 0, 0, 1); // OXP is coming!
    await mock.advanceTime(2000);
    assert.containsOnce($, ".o-mail-Activity");
    assert.containsOnce($, ".o-mail-Activity .text-warning");
    assert.containsOnce($, ".o-mail-Activity:contains('Today:')");
});

QUnit.test("activity with a summary layout", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        res_id: partnerId,
        res_model: "res.partner",
        summary: "test summary",
    });
    const { openView } = await start();
    await openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-mail-Activity-info:contains('test summary')");
});

QUnit.test("activity without summary layout", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        activity_type_id: 1,
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { openView } = await start();
    await openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-mail-Activity-info:contains('Email')");
});

QUnit.test("activity details toggle", async (assert) => {
    patchDate(2023, 0, 11, 12, 0, 0);
    const today = new Date();
    const tomorrow = new Date();
    tomorrow.setDate(today.getDate() + 1);
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["mail.activity"].create({
        create_date: date_to_str(today),
        create_uid: userId,
        date_deadline: date_to_str(tomorrow),
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { openView } = await start();
    await openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-mail-Activity");
    assert.containsNone($, ".o-mail-Activity-details");
    assert.containsOnce($, ".o-mail-Activity-info i[aria-label='Info']");

    await click(".o-mail-Activity-info i[aria-label='Info']");
    assert.containsOnce($, ".o-mail-Activity-details");

    await click(".o-mail-Activity-info i[aria-label='Info']");
    assert.containsNone($, ".o-mail-Activity-details");
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
    const { openView } = await start();
    await openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-mail-Activity");
    assert.containsOnce($, ".o-mail-Activity-sidebar");
    assert.containsOnce($, ".o-mail-Activity-mailTemplates");
    assert.containsOnce($, ".o-mail-ActivityMailTemplate-name");
    assert.strictEqual($(".o-mail-ActivityMailTemplate-name").text(), "Dummy mail template");
    assert.containsOnce($, ".o-mail-ActivityMailTemplate-preview");
    assert.containsOnce($, ".o-mail-ActivityMailTemplate-send");
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
    const { env, openView } = await start();
    await openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
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
    assert.containsOnce($, ".o-mail-Activity");
    assert.containsOnce($, ".o-mail-ActivityMailTemplate-preview");

    $(".o-mail-ActivityMailTemplate-preview")[0].click();
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
    const { openView } = await start({
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
    await openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-mail-Activity");
    assert.containsOnce($, ".o-mail-ActivityMailTemplate-send");

    click(".o-mail-ActivityMailTemplate-send").catch(() => {});
    assert.verifySteps(["activity_send_mail"]);
});

QUnit.test("activity click on mark as done", async (assert) => {
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
    const { openView } = await start();
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-mail-Activity");
    assert.containsOnce($, ".btn:contains('Mark Done')");

    await click(".btn:contains('Mark Done')");
    assert.containsOnce($, ".o-mail-ActivityMarkAsDone");

    await click(".btn:contains('Mark Done')");
    assert.containsNone($, ".o-mail-ActivityMarkAsDone");
});

QUnit.test(
    "activity mark as done popover should focus feedback input on open [REQUIRE FOCUS]",
    async (assert) => {
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
        const { openView } = await start();
        await openView({
            res_id: partnerId,
            res_model: "res.partner",
            views: [[false, "form"]],
        });
        assert.containsOnce($, ".o-mail-Activity");
        assert.containsOnce($, ".btn:contains('Mark Done')");

        await click(".btn:contains('Mark Done')");
        assert.strictEqual(
            $(".o-mail-ActivityMarkAsDone textarea[placeholder='Write Feedback']")[0],
            document.activeElement
        );
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
    const { env, openView } = await start();
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    patchWithCleanup(env.services.action, {
        doAction(action) {
            assert.step("do_action");
            assert.strictEqual(action.context.default_res_id, partnerId);
            assert.strictEqual(action.context.default_res_model, "res.partner");
            assert.strictEqual(action.type, "ir.actions.act_window");
            assert.strictEqual(action.res_model, "mail.activity");
            assert.strictEqual(action.res_id, activityId);
            return this._super(...arguments);
        },
    });
    assert.containsOnce($, ".o-mail-Activity");
    assert.containsOnce($, ".btn:contains('Edit')");

    await click(".btn:contains('Edit')");
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
    const { openView } = await start({
        async mockRPC(route, args) {
            if (route === "/web/dataset/call_kw/mail.activity/unlink") {
                assert.step("unlink");
                assert.strictEqual(args.args[0].length, 1);
                assert.strictEqual(args.args[0][0], activityId);
            }
        },
    });
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-mail-Activity");
    assert.containsOnce($, ".o-mail-Activity span:contains(Cancel)");

    await click(".o-mail-Activity span:contains(Cancel)");
    assert.verifySteps(["unlink"]);
    assert.containsNone($, ".o-mail-Activity");
});

QUnit.test("activity mark done popover close on ESCAPE", async (assert) => {
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
    const { openView } = await start();
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });

    await click(".btn:contains('Mark Done')");
    assert.containsOnce($, ".o-mail-ActivityMarkAsDone");

    await afterNextRender(() => triggerHotkey("Escape"));
    assert.containsNone($, ".o-mail-ActivityMarkAsDone");
});

QUnit.test("activity mark done popover click on discard", async (assert) => {
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
    const { openView } = await start();
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });

    await click(".btn:contains('Mark Done')");
    assert.containsOnce($, ".o-mail-ActivityMarkAsDone");
    assert.containsOnce($, ".o-mail-ActivityMarkAsDone button:contains(Discard)");
    await click(".o-mail-ActivityMarkAsDone button:contains(Discard)");
    assert.containsNone($, ".o-mail-ActivityMarkAsDone");
});

QUnit.test("Activity are sorted by deadline", async (assert) => {
    patchDate(2023, 0, 11, 12, 0, 0);
    const today = new Date();
    const dateBefore = new Date();
    dateBefore.setDate(today.getDate() - 5);
    const dateAfter = new Date();
    dateAfter.setDate(today.getDate() + 4);
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        date_deadline: date_to_str(dateAfter),
        res_id: partnerId,
        res_model: "res.partner",
        state: "planned",
    });
    pyEnv["mail.activity"].create({
        date_deadline: date_to_str(today),
        res_id: partnerId,
        res_model: "res.partner",
        state: "today",
    });
    pyEnv["mail.activity"].create({
        date_deadline: date_to_str(dateBefore),
        res_id: partnerId,
        res_model: "res.partner",
        state: "overdue",
    });
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId);
    assert.containsOnce($, ".o-mail-Activity:eq(0):contains(5 days overdue:)");
    assert.containsOnce($, ".o-mail-Activity:eq(1):contains(Today:)");
    assert.containsOnce($, ".o-mail-Activity:eq(2):contains(Due in 4 days:)");
});
