import { describe, expect, test } from "@odoo/hoot";
import {
    assertSteps,
    click,
    contains,
    defineMailModels,
    insertText,
    openFormView,
    start,
    startServer,
    step,
} from "../mail_test_helpers";
import { mockService, onRpc } from "@web/../tests/web_test_helpers";
import { Deferred } from "@odoo/hoot-mock";
import { getMockEnv } from "@web/../tests/_framework/env_test_helpers";
import { actionService } from "@web/webclient/actions/action_service";

describe.current.tags("desktop");
defineMailModels();

test("activity mark done popover simplest layout", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        activity_category: "not_upload_file",
        can_write: true,
        res_id: partnerId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".btn", { text: "Mark Done" });
    await contains(".o-mail-ActivityMarkAsDone");
    await contains(".o-mail-ActivityMarkAsDone textarea[placeholder='Write Feedback']");
    await contains(".o-mail-ActivityMarkAsDone button[aria-label='Done and Schedule Next']");
    await contains(".o-mail-ActivityMarkAsDone button[aria-label='Done']");
    await contains(".o-mail-ActivityMarkAsDone button", { text: "Discard" });
});

test("activity with force next mark done popover simplest layout", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const activityTypeId = pyEnv["mail.activity.type"].create({
        name: "TriggerType",
        chaining_type: "trigger",
    });
    pyEnv["mail.activity"].create({
        activity_category: "not_upload_file",
        activity_type_id: activityTypeId,
        can_write: true,
        res_id: partnerId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".btn", { text: "Mark Done" });
    await contains(".o-mail-ActivityMarkAsDone");
    await contains(".o-mail-ActivityMarkAsDone textarea[placeholder='Write Feedback']");
    await contains(".o-mail-ActivityMarkAsDone button[aria-label='Done and Schedule Next']");
    await contains(".o-mail-ActivityMarkAsDone button[aria-label='Done']", { count: 0 });
    await contains(".o-mail-ActivityMarkAsDone button", { text: "Discard" });
});

test("activity mark done popover mark done without feedback", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const activityId = pyEnv["mail.activity"].create({
        activity_category: "not_upload_file",
        can_write: true,
        res_id: partnerId,
        res_model: "res.partner",
    });
    onRpc("/web/dataset/call_kw/mail.activity/action_feedback", (request) => {
        step("action_feedback");
        const { params } = request.json();
        expect(params.args).toHaveLength(1);
        expect(params.args[0]).toHaveLength(1);
        expect(params.args[0][0]).toBe(activityId);
        expect(params.kwargs.attachment_ids).toBeEmpty();
        expect("feedback" in params.kwargs).toBe(false);
        // random value returned in order for the mock server to know that this route is implemented.
        return true;
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".btn", { text: "Mark Done" });
    await click(".o-mail-ActivityMarkAsDone button[aria-label='Done']");
    await assertSteps(["action_feedback"]);
});

test("activity mark done popover mark done with feedback", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const activityId = pyEnv["mail.activity"].create({
        activity_category: "not_upload_file",
        can_write: true,
        res_id: partnerId,
        res_model: "res.partner",
    });
    onRpc("/web/dataset/call_kw/mail.activity/action_feedback", (request) => {
        step("action_feedback");
        const { params } = request.json();
        expect(params.args).toHaveLength(1);
        expect(params.args[0]).toHaveLength(1);
        expect(params.args[0][0]).toBe(activityId);
        expect(params.kwargs.attachment_ids).toBeEmpty();
        expect(params.kwargs.feedback).toBe("This task is done");
        // random value returned in order for the mock server to know that this route is implemented.
        return true;
    });
    onRpc("/web/dataset/call_kw/mail.activity/unlink", () => {
        // 'unlink' on non-existing record raises a server crash
        throw new Error(
            "'unlink' RPC on activity must not be called (already unlinked from mark as done)"
        );
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".btn", { text: "Mark Done" });
    await insertText(
        ".o-mail-ActivityMarkAsDone textarea[placeholder='Write Feedback']",
        "This task is done"
    );
    await click(".o-mail-ActivityMarkAsDone button[aria-label='Done']");
    await assertSteps(["action_feedback"]);
});

test("activity mark done popover mark done and schedule next", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const activityId = pyEnv["mail.activity"].create({
        activity_category: "not_upload_file",
        can_write: true,
        res_id: partnerId,
        res_model: "res.partner",
    });
    onRpc("/web/dataset/call_kw/mail.activity/action_feedback_schedule_next", (request) => {
        step("action_feedback_schedule_next");
        const { params } = request.json();
        expect(params.args).toHaveLength(1);
        expect(params.args[0]).toHaveLength(1);
        expect(params.args[0][0]).toBe(activityId);
        expect(params.kwargs.feedback).toBe("This task is done");
        return false;
    });
    onRpc("/web/dataset/call_kw/mail.activity/unlink", () => {
        // 'unlink' on non-existing record raises a server crash
        throw new Error(
            "'unlink' RPC on activity must not be called (already unlinked from mark as done)"
        );
    });
    mockService("action", () => {
        const ogService = actionService.start(getMockEnv());
        return {
            ...ogService,
            doAction(action) {
                if (action?.res_model !== "res.partner") {
                    step("activity_action");
                    throw new Error(
                        "The do-action event should not be triggered when the route doesn't return an action"
                    );
                }
                ogService.doAction.call(this, ...arguments);
            },
        };
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".btn", { text: "Mark Done" });
    await insertText(
        ".o-mail-ActivityMarkAsDone textarea[placeholder='Write Feedback']",
        "This task is done"
    );
    await click(".o-mail-ActivityMarkAsDone button[aria-label='Done and Schedule Next']");
    await assertSteps(["action_feedback_schedule_next"]);
});

test("[technical] activity mark done & schedule next with new action", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        activity_category: "not_upload_file",
        can_write: true,
        res_id: partnerId,
        res_model: "res.partner",
    });
    onRpc("/web/dataset/call_kw/mail.activity/action_feedback_schedule_next", () => {
        return { type: "ir.actions.act_window" };
    });
    const def = new Deferred();
    mockService("action", () => {
        const ogService = actionService.start(getMockEnv());
        return {
            ...ogService,
            doAction(action) {
                if (action?.res_model !== "res.partner") {
                    def.resolve();
                    step("activity_action");
                    expect(action).toEqual(
                        { type: "ir.actions.act_window" },
                        { message: "The content of the action should be correct" }
                    );
                    return;
                }
                return ogService.doAction.call(this, ...arguments);
            },
        };
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".btn", { text: "Mark Done" });
    await click(".o-mail-ActivityMarkAsDone button[aria-label='Done and Schedule Next']");
    await def;
    await assertSteps(["activity_action"]);
});
