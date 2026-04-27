import { describe, expect, test } from "@odoo/hoot";
import { Deferred } from "@odoo/hoot-mock";

import {
    assertSteps,
    click,
    contains,
    start,
    startServer,
    step,
    openFormView,
} from "@mail/../tests/mail_test_helpers";
import { serverState, onRpc } from "@web/../tests/web_test_helpers";
import { defineApprovalsModels } from "@approvals/../tests/approvals_test_helpers";

describe.current.tags("desktop");
defineApprovalsModels();

test("activity with approval to be made by logged user", async () => {
    const pyEnv = await startServer();
    const requestId = pyEnv["approval.request"].create({});
    pyEnv["approval.approver"].create({
        request_id: requestId,
        status: "pending",
        user_id: serverState.userId,
    });
    pyEnv["mail.activity"].create({
        can_write: true,
        res_id: requestId,
        res_model: "approval.request",
        user_id: serverState.userId,
    });
    await start();
    await openFormView("approval.request", requestId);
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

test("activity with approval to be made by another user", async () => {
    const pyEnv = await startServer();
    const requestId = pyEnv["approval.request"].create({});
    const userId = pyEnv["res.users"].create({
        partner_id: pyEnv["res.partner"].create({}),
    });
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
    await start();
    await openFormView("approval.request", requestId);
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

test("approve approval", async () => {
    const pyEnv = await startServer();
    const requestId = pyEnv["approval.request"].create({});
    pyEnv["approval.approver"].create({
        request_id: requestId,
        status: "pending",
        user_id: serverState.userId,
    });
    pyEnv["mail.activity"].create({
        can_write: true,
        res_id: requestId,
        res_model: "approval.request",
        user_id: serverState.userId,
    });
    const def = new Deferred();
    onRpc("approval.approver", "action_approve", (args) => {
        expect(args.args.length).toBe(1);
        expect(args.args[0]).toBe(requestId);
        step("action_approve");
        def.resolve();
    });
    await start();
    await openFormView("approval.request", requestId);
    await click(".o-mail-Activity button", { text: "Approve" });
    await def;
    assertSteps(["action_approve"]);
});

test("refuse approval", async () => {
    const pyEnv = await startServer();
    const requestId = pyEnv["approval.request"].create({});
    pyEnv["approval.approver"].create({
        request_id: requestId,
        status: "pending",
        user_id: serverState.userId,
    });
    pyEnv["mail.activity"].create({
        can_write: true,
        res_id: requestId,
        res_model: "approval.request",
        user_id: serverState.userId,
    });
    const def = new Deferred();
    onRpc("approval.approver", "action_refuse", (args) => {
        expect(args.args.length).toBe(1);
        expect(args.args[0]).toBe(requestId);
        step("action_refuse");
        def.resolve();
    });
    await start();
    await openFormView("approval.request", requestId);
    await click(".o-mail-Activity button", { text: "Refuse" });
    await def;
    assertSteps(["action_refuse"]);
});
