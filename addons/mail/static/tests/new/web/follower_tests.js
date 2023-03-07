/** @odoo-module **/

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";

import { editInput, getFixture, makeDeferred, patchWithCleanup } from "@web/../tests/helpers/utils";

let target;
QUnit.module("follower", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("base rendering not editable", async function (assert) {
    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv["res.partner"].create([{}, {}]);
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: "res.partner",
    });
    const { openView } = await start({
        async mockRPC(route, args, performRpc) {
            if (route === "/mail/thread/data") {
                // mimic user without write access
                const res = await performRpc(...arguments);
                res["hasWriteAccess"] = false;
                return res;
            }
        },
    });
    await openView({
        res_id: threadId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await click(".o-mail-chatter-topbar-follower-list-button");
    assert.containsOnce(target, ".o-mail-chatter-topbar-follower-list-follower");
    assert.containsOnce(target, ".o-mail-chatter-topbar-follower-list-follower-details");
    assert.containsOnce(target, ".o-mail-chatter-topbar-follower-list-follower-avatar");
    assert.containsNone(target, ".o-mail-chatter-topbar-follower-list-follower-button");
});

QUnit.test("base rendering editable", async function (assert) {
    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv["res.partner"].create([{}, {}]);
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: "res.partner",
    });
    const { openView } = await start();
    await openView({
        res_id: threadId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await click(".o-mail-chatter-topbar-follower-list-button");
    assert.containsOnce(target, ".o-mail-chatter-topbar-follower-list-follower");
    assert.containsOnce(target, ".o-mail-chatter-topbar-follower-list-follower-details");
    assert.containsOnce(target, ".o-mail-chatter-topbar-follower-list-follower-avatar");
    assert.containsOnce(target, ".o-mail-chatter-topbar-follower-list-follower");
    assert.containsOnce(target, "button[title='Edit subscription']");
    assert.containsOnce(target, "button[title='Remove this follower']");
});

QUnit.test("click on partner follower details", async function (assert) {
    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv["res.partner"].create([{}, {}]);
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: "res.partner",
    });
    const openFormDef = makeDeferred();
    const { env, openView } = await start();
    await openView({
        res_id: threadId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    patchWithCleanup(env.services.action, {
        doAction(action) {
            assert.step("do_action");
            assert.strictEqual(action.res_id, partnerId);
            assert.strictEqual(action.res_model, "res.partner");
            assert.strictEqual(action.type, "ir.actions.act_window");
            openFormDef.resolve();
        },
    });
    await click(".o-mail-chatter-topbar-follower-list-button");
    assert.containsOnce(target, ".o-mail-chatter-topbar-follower-list-follower");
    assert.containsOnce(target, ".o-mail-chatter-topbar-follower-list-follower-details");

    document.querySelector(".o-mail-chatter-topbar-follower-list-follower-details").click();
    await openFormDef;
    assert.verifySteps(["do_action"], "redirect to partner profile");
});

QUnit.test("click on edit follower", async function (assert) {
    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv["res.partner"].create([{}, {}]);
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: "res.partner",
    });
    const { openView } = await start({
        async mockRPC(route, args) {
            if (route.includes("/mail/read_subscription_data")) {
                assert.step("fetch_subtypes");
            }
        },
    });
    await openView({
        res_id: threadId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await click(".o-mail-chatter-topbar-follower-list-button");
    assert.containsOnce(target, ".o-mail-chatter-topbar-follower-list-follower");
    assert.containsOnce(target, "button[title='Edit subscription']");

    await click("button[title='Edit subscription']");
    assert.verifySteps(["fetch_subtypes"]);
    assert.containsOnce(target, ".o-mail-follower-subtype-dialog");
});

QUnit.test("edit follower and close subtype dialog", async function (assert) {
    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv["res.partner"].create([{}, {}]);
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: "res.partner",
    });
    const { openView } = await start({
        async mockRPC(route, args) {
            if (route.includes("/mail/read_subscription_data")) {
                assert.step("fetch_subtypes");
            }
        },
    });
    await openView({
        res_id: threadId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await click(".o-mail-chatter-topbar-follower-list-button");
    assert.containsOnce(target, ".o-mail-chatter-topbar-follower-list-follower");
    assert.containsOnce(target, "button[title='Edit subscription']");

    await click("button[title='Edit subscription']");
    assert.verifySteps(["fetch_subtypes"]);
    assert.containsOnce(target, ".o-mail-follower-subtype-dialog");

    await click(".o-mail-follower-subtype-dialog button:contains(Cancel)");
    assert.containsNone(target, ".o-mail-follower-subtype-dialog");
});

QUnit.test("remove a follower in a dirty form view", async function (assert) {
    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv["res.partner"].create([{}, {}]);
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: "res.partner",
    });
    const { openFormView } = await start({
        async mockRPC(route, args) {
            if (args.method === "read") {
                assert.step(`read ${args.args[0][0]}`);
            }
        },
    });
    await openFormView("res.partner", threadId);
    assert.strictEqual(
        target.querySelector(".o-mail-chatter-topbar-followers-count").innerText,
        "1"
    );
    assert.verifySteps([`read ${threadId}`]);

    await editInput(target, ".o_field_char[name=name] input", "some value");
    await click(".o-mail-chatter-topbar-follower-list-button");
    assert.containsOnce(target, ".o-mail-chatter-topbar-follower-list-follower");

    await click("button[title='Remove this follower']");
    assert.strictEqual(
        target.querySelector(".o-mail-chatter-topbar-followers-count").innerText,
        "0"
    );
    assert.strictEqual(target.querySelector(".o_field_char[name=name] input").value, "some value");
    assert.verifySteps([`read ${threadId}`]);
});
