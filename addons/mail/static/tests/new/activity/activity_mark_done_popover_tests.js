/** @odoo-module **/

import { click, insertText, start, startServer } from "@mail/../tests/helpers/test_utils";

import { getFixture, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";

let target;

QUnit.module("activity mark as done popover", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("activity mark done popover simplest layout", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        activity_category: "not_upload_file",
        can_write: true,
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { openView } = await start();
    await openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
    await click(".btn:contains('Mark Done')");
    assert.containsOnce(target, ".o-mail-activity-mark-as-done");
    assert.containsOnce(
        target,
        ".o-mail-activity-mark-as-done textarea[placeholder='Write Feedback']"
    );
    assert.containsOnce(target, ".o-mail-activity-mark-as-done-buttons");
    assert.containsOnce(
        target,
        ".o-mail-activity-mark-as-done button[aria-label='Done and Schedule Next']"
    );
    assert.containsOnce(target, ".o-mail-activity-mark-as-done button[aria-label='Done']");
    assert.containsOnce(target, ".o-mail-activity-mark-as-done button:contains(Discard)");
});

QUnit.test("activity with force next mark done popover simplest layout", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        activity_category: "not_upload_file",
        can_write: true,
        chaining_type: "trigger",
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { openView } = await start();
    await openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
    await click(".btn:contains('Mark Done')");
    assert.containsOnce(target, ".o-mail-activity-mark-as-done");
    assert.containsOnce(
        target,
        ".o-mail-activity-mark-as-done textarea[placeholder='Write Feedback']"
    );
    assert.containsOnce(target, ".o-mail-activity-mark-as-done-buttons");
    assert.containsOnce(
        target,
        ".o-mail-activity-mark-as-done button[aria-label='Done and Schedule Next']"
    );
    assert.containsNone(target, ".o-mail-activity-mark-as-done button[aria-label='Done']");
    assert.containsOnce(target, ".o-mail-activity-mark-as-done button:contains(Discard)");
});

QUnit.test("activity mark done popover mark done without feedback", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const activityId = pyEnv["mail.activity"].create({
        activity_category: "not_upload_file",
        can_write: true,
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { openView } = await start({
        async mockRPC(route, args) {
            if (route === "/web/dataset/call_kw/mail.activity/action_feedback") {
                assert.step("action_feedback");
                assert.strictEqual(args.args.length, 1);
                assert.strictEqual(args.args[0].length, 1);
                assert.strictEqual(args.args[0][0], activityId);
                assert.strictEqual(args.kwargs.attachment_ids.length, 0);
                assert.notOk(args.kwargs.feedback);
                // random value returned in order for the mock server to know that this route is implemented.
                return true;
            }
            if (route === "/web/dataset/call_kw/mail.activity/unlink") {
                // 'unlink' on non-existing record raises a server crash
                throw new Error(
                    "'unlink' RPC on activity must not be called (already unlinked from mark as done)"
                );
            }
        },
    });
    await openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
    await click(".btn:contains('Mark Done')");
    await click(".o-mail-activity-mark-as-done button[aria-label='Done']");
    assert.verifySteps(["action_feedback"]);
});

QUnit.test("activity mark done popover mark done with feedback", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const activityId = pyEnv["mail.activity"].create({
        activity_category: "not_upload_file",
        can_write: true,
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { openView } = await start({
        async mockRPC(route, args) {
            if (route === "/web/dataset/call_kw/mail.activity/action_feedback") {
                assert.step("action_feedback");
                assert.strictEqual(args.args.length, 1);
                assert.strictEqual(args.args[0].length, 1);
                assert.strictEqual(args.args[0][0], activityId);
                assert.strictEqual(args.kwargs.attachment_ids.length, 0);
                assert.strictEqual(args.kwargs.feedback, "This task is done");
                // random value returned in order for the mock server to know that this route is implemented.
                return true;
            }
            if (route === "/web/dataset/call_kw/mail.activity/unlink") {
                // 'unlink' on non-existing record raises a server crash
                throw new Error(
                    "'unlink' RPC on activity must not be called (already unlinked from mark as done)"
                );
            }
        },
    });
    await openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
    await click(".btn:contains('Mark Done')");
    insertText(
        ".o-mail-activity-mark-as-done textarea[placeholder='Write Feedback']",
        "This task is done"
    ).catch(() => {}); // no render
    await nextTick();
    await click(".o-mail-activity-mark-as-done button[aria-label='Done']");
    assert.verifySteps(["action_feedback"]);
});

QUnit.test("activity mark done popover mark done and schedule next", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const activityId = pyEnv["mail.activity"].create({
        activity_category: "not_upload_file",
        can_write: true,
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { env, openView } = await start({
        async mockRPC(route, args) {
            if (route === "/web/dataset/call_kw/mail.activity/action_feedback_schedule_next") {
                assert.step("action_feedback_schedule_next");
                assert.strictEqual(args.args.length, 1);
                assert.strictEqual(args.args[0].length, 1);
                assert.strictEqual(args.args[0][0], activityId);
                assert.strictEqual(args.kwargs.feedback, "This task is done");
                return false;
            }
            if (route === "/web/dataset/call_kw/mail.activity/unlink") {
                // 'unlink' on non-existing record raises a server crash
                throw new Error(
                    "'unlink' RPC on activity must not be called (already unlinked from mark as done)"
                );
            }
        },
    });
    await openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
    patchWithCleanup(env.services.action, {
        doAction() {
            assert.step("activity_action");
            throw new Error(
                "The do-action event should not be triggered when the route doesn't return an action"
            );
        },
    });
    await click(".btn:contains('Mark Done')");
    insertText(
        ".o-mail-activity-mark-as-done textarea[placeholder='Write Feedback']",
        "This task is done"
    ).catch(() => {}); // no render
    await nextTick();
    await click(".o-mail-activity-mark-as-done button[aria-label='Done and Schedule Next']");
    assert.verifySteps(["action_feedback_schedule_next"]);
});

QUnit.test(
    "[technical] activity mark done & schedule next with new action",
    async function (assert) {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({});
        pyEnv["mail.activity"].create({
            activity_category: "not_upload_file",
            can_write: true,
            res_id: partnerId,
            res_model: "res.partner",
        });
        const { env, openView } = await start({
            async mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/mail.activity/action_feedback_schedule_next") {
                    return { type: "ir.actions.act_window" };
                }
            },
        });
        await openView({
            res_model: "res.partner",
            res_id: partnerId,
            views: [[false, "form"]],
        });
        patchWithCleanup(env.services.action, {
            doAction(action) {
                assert.step("activity_action");
                assert.deepEqual(
                    action,
                    { type: "ir.actions.act_window" },
                    "The content of the action should be correct"
                );
            },
        });
        await click(".btn:contains('Mark Done')");
        await click(".o-mail-activity-mark-as-done button[aria-label='Done and Schedule Next']");
        assert.verifySteps(["activity_action"]);
    }
);
