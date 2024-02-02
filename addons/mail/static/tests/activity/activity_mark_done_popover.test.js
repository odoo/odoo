/** @odoo-module */

import { expect, test } from "@odoo/hoot";
import {
    click,
    contains,
    defineMailModels,
    insertText,
    openFormView,
    start,
    startServer,
} from "../mail_test_helpers";
import { onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { Deferred } from "@odoo/hoot-mock";

defineMailModels();

test.skip("activity mark done popover simplest layout", async () => {
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

test.skip("activity with force next mark done popover simplest layout", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        activity_category: "not_upload_file",
        can_write: true,
        chaining_type: "trigger",
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

test.skip("activity mark done popover mark done without feedback", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const activityId = pyEnv["mail.activity"].create({
        activity_category: "not_upload_file",
        can_write: true,
        res_id: partnerId,
        res_model: "res.partner",
    });
    onRpc("/web/dataset/call_kw/mail.activity/action_feedback", (route, args) => {
        expect.step("action_feedback");
        expect(args.args.length).toBe(1);
        expect(args.args[0]).toHaveCount(1);
        expect(args.args[0][0]).toBe(activityId);
        expect(args.kwargs.attachment_ids).toBeEmpty();
        expect(args.kwargs.feedback).not.toBeTruthy();
        // random value returned in order for the mock server to know that this route is implemented.
        return true;
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".btn", { text: "Mark Done" });
    await click(".o-mail-ActivityMarkAsDone button[aria-label='Done']");
    expect(["action_feedback"]).toVerifySteps();
});

test.skip("activity mark done popover mark done with feedback", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const activityId = pyEnv["mail.activity"].create({
        activity_category: "not_upload_file",
        can_write: true,
        res_id: partnerId,
        res_model: "res.partner",
    });
    onRpc((route, args) => {
        if (route === "/web/dataset/call_kw/mail.activity/action_feedback") {
            expect.step("action_feedback");
            expect(args.args).toHaveCount(1);
            expect(args.args[0]).toHaveCount(1);
            expect(args.args[0][0]).toBe(activityId);
            expect(args.kwargs.attachment_ids).toBeEmpty();
            expect(args.kwargs.feedback).toBe("This task is done");
            // random value returned in order for the mock server to know that this route is implemented.
            return true;
        }
        if (route === "/web/dataset/call_kw/mail.activity/unlink") {
            // 'unlink' on non-existing record raises a server crash
            throw new Error(
                "'unlink' RPC on activity must not be called (already unlinked from mark as done)"
            );
        }
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".btn", { text: "Mark Done" });
    await insertText(
        ".o-mail-ActivityMarkAsDone textarea[placeholder='Write Feedback']",
        "This task is done"
    );
    await click(".o-mail-ActivityMarkAsDone button[aria-label='Done']");
    expect(["action_feedback"]).toVerifySteps();
});

test.skip("activity mark done popover mark done and schedule next", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const activityId = pyEnv["mail.activity"].create({
        activity_category: "not_upload_file",
        can_write: true,
        res_id: partnerId,
        res_model: "res.partner",
    });
    onRpc((route, args) => {
        if (route === "/web/dataset/call_kw/mail.activity/action_feedback_schedule_next") {
            expect.step("action_feedback_schedule_next");
            expect(args.args).toHaveCount(1);
            expect(args.args[0]).toHaveCount(1);
            expect(args.args[0][0]).toBe(activityId);
            expect(args.kwargs.feedback).toBe("This task is done");
            return false;
        }
        if (route === "/web/dataset/call_kw/mail.activity/unlink") {
            // 'unlink' on non-existing record raises a server crash
            throw new Error(
                "'unlink' RPC on activity must not be called (already unlinked from mark as done)"
            );
        }
    });
    const { env } = await start();
    await openFormView("res.partner", partnerId);
    patchWithCleanup(env.services.action, {
        doAction() {
            expect.step("activity_action");
            throw new Error(
                "The do-action event should not be triggered when the route doesn't return an action"
            );
        },
    });
    await click(".btn", { text: "Mark Done" });
    await insertText(
        ".o-mail-ActivityMarkAsDone textarea[placeholder='Write Feedback']",
        "This task is done"
    );
    await click(".o-mail-ActivityMarkAsDone button[aria-label='Done and Schedule Next']");
    expect(["action_feedback_schedule_next"]).toVerifySteps();
});

test.skip("[technical] activity mark done & schedule next with new action", async () => {
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
    const { env } = await start();
    await openFormView("res.partner", partnerId);
    const def = new Deferred();
    patchWithCleanup(env.services.action, {
        doAction(action) {
            def.resolve();
            expect.step("activity_action");
            expect(action).toEqual(
                { type: "ir.actions.act_window" },
                { message: "The content of the action should be correct" }
            );
        },
    });
    await click(".btn", { text: "Mark Done" });
    await click(".o-mail-ActivityMarkAsDone button[aria-label='Done and Schedule Next']");
    await def;
    expect(["activity_action"]).toVerifySteps();
});
