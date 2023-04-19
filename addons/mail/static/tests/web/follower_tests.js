/** @odoo-module **/

import { click, nextAnimationFrame, start, startServer } from "@mail/../tests/helpers/test_utils";

import { editInput, makeDeferred, patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module("follower");

QUnit.test("base rendering not editable", async (assert) => {
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
    await click(".o-mail-Followers-button");
    assert.containsOnce($, ".o-mail-Follower");
    assert.containsOnce($, ".o-mail-Follower-details");
    assert.containsOnce($, ".o-mail-Follower-avatar");
    assert.containsNone($, ".o-mail-Follower-action");
});

QUnit.test("base rendering editable", async (assert) => {
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
    await click(".o-mail-Followers-button");
    assert.containsOnce($, ".o-mail-Follower");
    assert.containsOnce($, ".o-mail-Follower-details");
    assert.containsOnce($, ".o-mail-Follower-avatar");
    assert.containsOnce($, ".o-mail-Follower");
    assert.containsOnce($, "button[title='Edit subscription']");
    assert.containsOnce($, "button[title='Remove this follower']");
});

QUnit.test("click on partner follower details", async (assert) => {
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
    await click(".o-mail-Followers-button");
    assert.containsOnce($, ".o-mail-Follower");
    assert.containsOnce($, ".o-mail-Follower-details");

    $(".o-mail-Follower-details")[0].click();
    await openFormDef;
    assert.verifySteps(["do_action"], "redirect to partner profile");
});

QUnit.test("click on edit follower", async (assert) => {
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
    await click(".o-mail-Followers-button");
    assert.containsOnce($, ".o-mail-Follower");
    assert.containsOnce($, "button[title='Edit subscription']");

    await click("button[title='Edit subscription']");
    assert.verifySteps(["fetch_subtypes"]);
    assert.containsOnce($, ".o-mail-FollowerSubtypeDialog");
});

QUnit.test("edit follower and close subtype dialog", async (assert) => {
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
    await click(".o-mail-Followers-button");
    assert.containsOnce($, ".o-mail-Follower");
    assert.containsOnce($, "button[title='Edit subscription']");

    await click("button[title='Edit subscription']");
    assert.verifySteps(["fetch_subtypes"]);
    assert.containsOnce($, ".o-mail-FollowerSubtypeDialog");

    await click(".o-mail-FollowerSubtypeDialog button:contains(Cancel)");
    assert.containsNone($, ".o-mail-FollowerSubtypeDialog");
});

QUnit.test("remove a follower in a dirty form view", async (assert) => {
    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv["res.partner"].create([{}, {}]);
    pyEnv["discuss.channel"].create({ name: "General", display_name: "General" });
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: "res.partner",
    });
    const views = {
        "res.partner,false,form": `
            <form>
                <field name="name"/>
                <field name="channel_ids" widget="many2many_tags" options="{'color_field': 'color'}"/>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                    <field name="message_follower_ids"/>
                </div>
            </form>`,
    };
    const { openFormView } = await start({ serverData: { views } });
    await openFormView("res.partner", threadId);
    click(".o_field_many2many_tags[name='channel_ids'] input").catch(() => {});
    await nextAnimationFrame();
    click(".dropdown-item:contains(General)").catch(() => {});
    await nextAnimationFrame();
    assert.containsOnce($, ".o_tag:contains(General)");
    assert.strictEqual($(".o-mail-Followers-counter")[0].innerText, "1");
    await editInput(document.body, ".o_field_char[name=name] input", "some value");
    await click(".o-mail-Followers-button");
    await click("button[title='Remove this follower']");
    assert.strictEqual($(".o-mail-Followers-counter")[0].innerText, "0");
    assert.strictEqual($(".o_field_char[name=name] input").val(), "some value");
    assert.containsOnce($, ".o_tag:contains(General)");
});

QUnit.test("removing a follower should reload form view", async function (assert) {
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
    assert.verifySteps([`read ${threadId}`]);
    await click(".o-mail-Followers-button");
    await click("button[title='Remove this follower']");
    assert.verifySteps([`read ${threadId}`]);
});
