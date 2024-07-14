/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { makeDeferred } from "@web/../tests/helpers/utils";
import { click, contains } from "@web/../tests/utils";

QUnit.module("activity (patch)");

QUnit.test("activity with approval to be made by logged user", async () => {
    const pyEnv = await startServer();
    const requestId = pyEnv["approval.request"].create({});
    pyEnv["approval.approver"].create({
        request_id: requestId,
        status: "pending",
        user_id: pyEnv.currentUserId,
    });
    pyEnv["mail.activity"].create({
        can_write: true,
        res_id: requestId,
        res_model: "approval.request",
        user_id: pyEnv.currentUserId,
    });
    const { openView } = await start();
    await openView({
        res_model: "approval.request",
        res_id: requestId,
        views: [[false, "form"]],
    });
    await contains(".o-mail-Activity");
    await contains(".o-mail-Activity-sidebar");
    await contains(".o-mail-Activity-user");
    await contains(".o-mail-Activity-note", { count: 0 });
    await contains(".o-mail-Activity-details", { count: 0 });
    await contains(".o-mail-Activity-mailTemplates", { count: 0 });
    await contains(".o-mail-Activity .btn", { count: 0, text: "Edit" });
    await contains(".o-mail-Activity .btn", { count: 0, text: "Cancel" });
    await contains(".o-mail-Activity .btn", { count: 0, text: "Mark Done" });
    await contains(".o-mail-Activity .btn", { count: 0, text: "Upload Document" });
    await contains(".o-mail-Activity button", { text: "Approve" });
    await contains(".o-mail-Activity button", { text: "Refuse" });
});

QUnit.test("activity with approval to be made by another user", async () => {
    const pyEnv = await startServer();
    const requestId = pyEnv["approval.request"].create({});
    const userId = pyEnv["res.users"].create({});
    pyEnv["approval.approver"].create({
        request_id: requestId,
        status: "pending",
        user_id: userId,
    });
    pyEnv["mail.activity"].create({
        can_write: true,
        res_id: requestId,
        res_model: "approval.request",
        user_id: userId,
    });
    const { openView } = await start();
    await openView({
        res_model: "approval.request",
        res_id: requestId,
        views: [[false, "form"]],
    });
    await contains(".o-mail-Activity");
    await contains(".o-mail-Activity-sidebar");
    await contains(".o-mail-Activity-user");
    await contains(".o-mail-Activity-note", { count: 0 });
    await contains(".o-mail-Activity-details", { count: 0 });
    await contains(".o-mail-Activity-mailTemplates", { count: 0 });
    await contains(".o-mail-Activity .btn", { count: 0, text: "Edit" });
    await contains(".o-mail-Activity .btn", { count: 0, text: "Cancel" });
    await contains(".o-mail-Activity .btn", { count: 0, text: "Mark Done" });
    await contains(".o-mail-Activity .btn", { count: 0, text: "Upload Document" });
    await contains(".o-mail-Activity button", { count: 0, text: "Approve" });
    await contains(".o-mail-Activity button", { count: 0, text: "Refuse" });
    await contains(".o-mail-Activity span", { text: "To Approve" });
});

QUnit.test("approve approval", async (assert) => {
    const pyEnv = await startServer();
    const requestId = pyEnv["approval.request"].create({});
    pyEnv["approval.approver"].create({
        request_id: requestId,
        status: "pending",
        user_id: pyEnv.currentUserId,
    });
    pyEnv["mail.activity"].create({
        can_write: true,
        res_id: requestId,
        res_model: "approval.request",
        user_id: pyEnv.currentUserId,
    });
    const def = makeDeferred();
    const { openView } = await start({
        async mockRPC(route, args) {
            if (args.method === "action_approve") {
                assert.strictEqual(args.args.length, 1);
                assert.strictEqual(args.args[0], requestId);
                assert.step("action_approve");
                def.resolve();
            }
        },
    });
    await openView({
        res_model: "approval.request",
        res_id: requestId,
        views: [[false, "form"]],
    });
    await click(".o-mail-Activity button", { text: "Approve" });
    await def;
    assert.verifySteps(["action_approve"]);
});

QUnit.test("refuse approval", async (assert) => {
    const pyEnv = await startServer();
    const requestId = pyEnv["approval.request"].create({});
    pyEnv["approval.approver"].create({
        request_id: requestId,
        status: "pending",
        user_id: pyEnv.currentUserId,
    });
    pyEnv["mail.activity"].create({
        can_write: true,
        res_id: requestId,
        res_model: "approval.request",
        user_id: pyEnv.currentUserId,
    });
    const def = makeDeferred();
    const { openView } = await start({
        async mockRPC(route, args) {
            if (args.method === "action_refuse") {
                assert.strictEqual(args.args.length, 1);
                assert.strictEqual(args.args[0], requestId);
                assert.step("action_refuse");
                def.resolve();
            }
        },
    });
    await openView({
        res_model: "approval.request",
        res_id: requestId,
        views: [[false, "form"]],
    });
    await click(".o-mail-Activity button", { text: "Refuse" });
    await def;
    assert.verifySteps(["action_refuse"]);
});
