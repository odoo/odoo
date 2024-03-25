import { describe, expect, test } from "@odoo/hoot";

import { deserializeDateTime, serializeDate, today } from "@web/core/l10n/dates";
import {
    assertSteps,
    click,
    contains,
    createFile,
    defineMailModels,
    inputFiles,
    openFormView,
    start,
    startServer,
    step,
    triggerHotkey,
} from "../mail_test_helpers";
import { mockService, onRpc, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";
import { advanceTime, mockDate } from "@odoo/hoot-mock";
import { getOrigin } from "@web/core/utils/urls";
import { getMockEnv } from "@web/../tests/_framework/env_test_helpers";
import { actionService } from "@web/webclient/actions/action_service";

describe.current.tags("desktop");
defineMailModels();

test("activity upload document is available", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const activityType = pyEnv["mail.activity.type"]._records.find(
        (r) => r.name === "Upload Document"
    );
    pyEnv["mail.activity"].create({
        activity_category: "upload_file",
        activity_type_id: activityType.id,
        can_write: true,
        res_id: partnerId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity .btn", { text: "Upload Document" });
    await contains(".btn .fa-upload");
    await contains(".o-mail-Activity .o_input_file");
});

test("activity can upload a document", async () => {
    const pyEnv = await startServer();
    const fakeId = pyEnv["res.partner"].create({});
    const activityType = pyEnv["mail.activity.type"]._records.find(
        (r) => r.name === "Upload Document"
    );
    pyEnv["mail.activity"].create({
        activity_category: "upload_file",
        activity_type_id: activityType.id,
        can_write: true,
        res_id: fakeId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", fakeId, {
        arch: `
            <form string="Fake">
                <sheet></sheet>
                <chatter/>
            </form>`,
    });
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

test("activity simplest layout", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        res_id: partnerId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", partnerId);
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

test("activity with note layout", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        note: "<p>There is no good or bad note</p>",
        res_id: partnerId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity");
    await contains(".o-mail-Activity-note", { text: "There is no good or bad note" });
});

test("activity info layout when planned after tomorrow", async () => {
    mockDate("2023-01-11 12:00:00");
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        date_deadline: serializeDate(today().plus({ days: 5 })),
        res_id: partnerId,
        res_model: "res.partner",
        state: "planned",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity span.text-success", { text: "Due in 5 days:" });
});

test("activity info layout when planned tomorrow", async () => {
    mockDate("2023-01-11 12:00:00");
    const tomorrow = today().plus({ days: 1 });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        date_deadline: serializeDate(tomorrow),
        res_id: partnerId,
        res_model: "res.partner",
        state: "planned",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity span.text-success", { text: "Tomorrow:" });
});

test("activity info layout when planned today", async () => {
    mockDate("2023-01-11 12:00:00");
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        date_deadline: serializeDate(today()),
        res_id: partnerId,
        res_model: "res.partner",
        state: "today",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity span.text-warning", { text: "Today:" });
});

test("activity info layout when planned yesterday", async () => {
    mockDate("2023-01-11 12:00:00");
    const yesterday = today().plus({ days: -1 });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        date_deadline: serializeDate(yesterday),
        res_id: partnerId,
        res_model: "res.partner",
        state: "overdue",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity span.text-danger", { text: "Yesterday:" });
});

test("activity info layout when planned before yesterday", async () => {
    mockDate("2023-01-11 12:00:00");
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        date_deadline: serializeDate(today().plus({ days: -5 })),
        res_id: partnerId,
        res_model: "res.partner",
        state: "overdue",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity span.text-danger", { text: "5 days overdue:" });
});

test.skip("activity info layout change at midnight", async () => {
    // skip: does not work consistently both locally and on runbot at the same time (tz issue?)
    mockDate("2023-12-07 23:59:59", 0);
    const tomorrow = today().plus({ days: 1 });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        date_deadline: serializeDate(tomorrow),
        res_id: partnerId,
        res_model: "res.partner",
        state: "planned",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity span.text-success", { text: "Tomorrow:" });
    mockDate("2023-12-08 00:00:01");
    await advanceTime(2000);
    await contains(".o-mail-Activity span.text-warning", { text: "Today:" });
});

test("activity with a summary layout", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        res_id: partnerId,
        res_model: "res.partner",
        summary: "test summary",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity", { text: "“test summary”" });
});

test("activity without summary layout", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        activity_type_id: 1,
        res_id: partnerId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity", { text: "Email" });
});

test("activity details toggle", async () => {
    mockDate("2023-01-11 12:00:00");
    const tomorrow = today().plus({ days: 1 });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["mail.activity"].create({
        create_uid: userId,
        date_deadline: serializeDate(tomorrow),
        res_id: partnerId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity");
    await contains(".o-mail-Activity-details", { count: 0 });
    await contains(".o-mail-Activity i[aria-label='Info']");
    await click(".o-mail-Activity i[aria-label='Info']");
    await contains(".o-mail-Activity-details");
    await click(".o-mail-Activity i[aria-label='Info']");
    await contains(".o-mail-Activity-details", { count: 0 });
});

test("activity with mail template layout", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const mailTemplateId = pyEnv["mail.template"].create({ name: "Dummy mail template" });
    const activityType = pyEnv["mail.activity.type"]._records.find((r) => r.name === "Email");
    pyEnv["mail.activity.type"].write(activityType.id, { mail_template_ids: [mailTemplateId] });
    pyEnv["mail.activity"].create({
        activity_type_id: activityType.id,
        res_id: partnerId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity");
    await contains(".o-mail-Activity-sidebar");
    await contains(".o-mail-Activity-mailTemplates");
    await contains(".o-mail-ActivityMailTemplate-name", { text: "Dummy mail template" });
    await contains(".o-mail-ActivityMailTemplate-preview");
    await contains(".o-mail-ActivityMailTemplate-send");
});

test("activity with mail template: preview mail", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const mailTemplateId = pyEnv["mail.template"].create({ name: "Dummy mail template" });
    const activityType = pyEnv["mail.activity.type"]._records.find((r) => r.name === "Email");
    pyEnv["mail.activity.type"].write(activityType.id, { mail_template_ids: [mailTemplateId] });
    pyEnv["mail.activity"].create({
        activity_type_id: activityType.id,
        res_id: partnerId,
        res_model: "res.partner",
    });
    mockService("action", () => {
        const ogService = actionService.start(getMockEnv());
        return {
            ...ogService,
            doAction(action) {
                if (action?.res_model !== "res.partner") {
                    // Click on Preview Mail Template
                    step("do_action");
                    expect(action.context.default_res_ids).toEqual([partnerId]);
                    expect(action.context.default_model).toBe("res.partner");
                    expect(action.context.default_template_id).toBe(mailTemplateId);
                    expect(action.type).toBe("ir.actions.act_window");
                    expect(action.res_model).toBe("mail.compose.message");
                }
                return ogService.doAction.call(this, ...arguments);
            },
        };
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity");
    await contains(".o-mail-ActivityMailTemplate-preview");
    await click(".o-mail-ActivityMailTemplate-preview");
    await assertSteps(["do_action"]);
});

test("activity with mail template: send mail", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const mailTemplateId = pyEnv["mail.template"].create({ name: "Dummy mail template" });
    const activityType = pyEnv["mail.activity.type"]._records.find((r) => r.name === "Email");
    pyEnv["mail.activity.type"].write(activityType.id, { mail_template_ids: [mailTemplateId] });
    pyEnv["mail.activity"].create({
        activity_type_id: activityType.id,
        res_id: partnerId,
        res_model: "res.partner",
    });
    onRpc("/web/dataset/call_kw/res.partner/activity_send_mail", (request) => {
        step("activity_send_mail");
        const { params } = request.json();
        expect(params.args[0]).toHaveLength(1);
        expect(params.args[0][0]).toBe(partnerId);
        expect(params.args[1]).toBe(mailTemplateId);
        // random value returned in order for the mock server to know that this route is implemented.
        return true;
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity");
    await contains(".o-mail-ActivityMailTemplate-send");
    await click(".o-mail-ActivityMailTemplate-send");
    await assertSteps(["activity_send_mail"]);
});

test("activity click on mark as done", async () => {
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
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity");
    await click(".btn", { text: "Mark Done" });
    await contains(".o-mail-ActivityMarkAsDone");
    await click(".btn", { text: "Mark Done" });
    await contains(".o-mail-ActivityMarkAsDone", { count: 0 });
});

test("activity mark as done popover should focus feedback input on open [REQUIRE FOCUS]", async () => {
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
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity");
    await click(".btn", { text: "Mark Done" });
    await contains(".o-mail-ActivityMarkAsDone textarea[placeholder='Write Feedback']:focus");
});

test("activity click on edit", async () => {
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
    mockService("action", () => {
        const mockedActionService = actionService.start(getMockEnv());
        patchWithCleanup(mockedActionService, {
            doAction(action) {
                if (action?.res_model !== "res.partner") {
                    step("do_action");
                    expect(action.type).toBe("ir.actions.act_window");
                    expect(action.res_model).toBe("mail.activity");
                    expect(action.res_id).toBe(activityId);
                }
                return super.doAction(...arguments);
            },
        });
        return mockedActionService;
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Activity .btn", { text: "Edit" });
    await assertSteps(["do_action"]);
});

test("activity click on cancel", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const activityTypeId = pyEnv["mail.activity.type"].search([["name", "=", "Email"]])[0];
    const activityId = pyEnv["mail.activity"].create({
        activity_type_id: activityTypeId,
        can_write: true,
        res_id: partnerId,
        res_model: "res.partner",
    });
    onRpc("/web/dataset/call_kw/mail.activity/unlink", (request) => {
        step("unlink");
        const { params } = request.json();
        expect(params.args[0]).toHaveLength(1);
        expect(params.args[0][0]).toBe(activityId);
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Activity .btn", { text: "Cancel" });
    await contains(".o-mail-Activity", { count: 0 });
    await assertSteps(["unlink"]);
});

test("activity mark done popover close on ESCAPE", async () => {
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
    await start();
    await openFormView("res.partner", partnerId);
    await click(".btn", { text: "Mark Done" });
    await contains(".o-mail-ActivityMarkAsDone");
    triggerHotkey("Escape");
    await contains(".o-mail-ActivityMarkAsDone", { count: 0 });
});

test("activity mark done popover click on discard", async () => {
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
    await start();
    await openFormView("res.partner", partnerId);
    await click(".btn", { text: "Mark Done" });
    await click(".o-mail-ActivityMarkAsDone button", { text: "Discard" });
    await contains(".o-mail-ActivityMarkAsDone", { count: 0 });
});

test("Activity are sorted by deadline", async () => {
    mockDate("2023-01-11 12:00:00");
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
    await start();
    await openFormView("res.partner", partnerId);
    await contains(":nth-child(1 of .o-mail-Activity)", { text: "5 days overdue:" });
    await contains(":nth-child(2 of .o-mail-Activity)", { text: "Today:" });
    await contains(":nth-child(3 of .o-mail-Activity)", { text: "Due in 4 days:" });
});

test("chatter 'activities' button open the activity schedule wizard", async () => {
    const pyEnv = await startServer();
    const fakeId = pyEnv["res.partner"].create({});
    mockService("action", () => {
        const ogService = actionService.start(getMockEnv());
        return {
            ...ogService,
            doAction(action, options) {
                if (action?.res_model !== "res.partner") {
                    step("doAction");
                    const expectedAction = {
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
                    expect(action).toEqual(expectedAction, {
                        message: "should execute an action with correct params",
                    });
                    options.onClose();
                    return Promise.resolve();
                }
                return ogService.doAction.call(this, ...arguments);
            },
        };
    });
    await start();
    await openFormView("res.partner", fakeId, {
        arch: `
            <form string="Fake">
                <sheet></sheet>
                <chatter/>
            </form>`,
    });
    await click("button", { text: "Activities" });
    await assertSteps(["doAction"]);
});

test("Activity avatar should have a unique timestamp", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        res_id: partnerId,
        res_model: "res.partner",
    });
    await start();
    const partner = pyEnv["res.partner"].search_read([["id", "=", serverState.partnerId]])[0];
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity");
    await contains(
        `.o-mail-Activity-sidebar img[data-src="${getOrigin()}/web/image/res.partner/${
            serverState.partnerId
        }/avatar_128?unique=${deserializeDateTime(partner.write_date).ts}`
    );
});
