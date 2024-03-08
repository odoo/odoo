/** @odoo-module alias=@mail/../tests/chatter/web/follower_tests default=false */
const test = QUnit.test; // QUnit.test()

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { openFormView, start } from "@mail/../tests/helpers/test_utils";

import { editInput, makeDeferred, patchWithCleanup } from "@web/../tests/helpers/utils";
import { assertSteps, click, contains, step } from "@web/../tests/utils";

QUnit.module("follower");

test("base rendering not editable", async () => {
    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv["res.partner"].create([{}, {}]);
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: "res.partner",
    });
    await start({
        async mockRPC(route, args, performRpc) {
            if (route === "/mail/thread/data") {
                // mimic user without write access
                const res = await performRpc(...arguments);
                res["hasWriteAccess"] = false;
                return res;
            }
        },
    });
    await openFormView("res.partner", threadId);
    await click(".o-mail-Followers-button");
    await contains(".o-mail-Follower");
    await contains(".o-mail-Follower-details");
    await contains(".o-mail-Follower-avatar");
    await contains(".o-mail-Follower-action", { count: 0 });
});

test("base rendering editable", async () => {
    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv["res.partner"].create([{}, {}]);
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", threadId);
    await click(".o-mail-Followers-button");
    await contains(".o-mail-Follower");
    await contains(".o-mail-Follower-details");
    await contains(".o-mail-Follower-avatar");
    await contains(".o-mail-Follower");
    await contains("button[title='Edit subscription']");
    await contains("button[title='Remove this follower']");
});

test("click on partner follower details", async (assert) => {
    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv["res.partner"].create([{}, {}]);
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: "res.partner",
    });
    const openFormDef = makeDeferred();
    const { env } = await start();
    await openFormView("res.partner", threadId);
    patchWithCleanup(env.services.action, {
        doAction(action) {
            step("do_action");
            assert.strictEqual(action.res_id, partnerId);
            assert.strictEqual(action.res_model, "res.partner");
            assert.strictEqual(action.type, "ir.actions.act_window");
            openFormDef.resolve();
        },
    });
    await click(".o-mail-Followers-button");
    await contains(".o-mail-Follower");
    await contains(".o-mail-Follower-details");

    $(".o-mail-Follower-details")[0].click();
    await openFormDef;
    await assertSteps(["do_action"], "redirect to partner profile");
});

test("click on edit follower", async () => {
    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv["res.partner"].create([{}, {}]);
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: "res.partner",
    });
    await start({
        async mockRPC(route, args) {
            if (route.includes("/mail/read_subscription_data")) {
                step("fetch_subtypes");
            }
        },
    });
    await openFormView("res.partner", threadId);
    await click(".o-mail-Followers-button");
    await contains(".o-mail-Follower");
    await contains("button[title='Edit subscription']");

    await click("button[title='Edit subscription']");
    await contains(".o-mail-Follower", { count: 0 });
    await assertSteps(["fetch_subtypes"]);
    await contains(".o-mail-FollowerSubtypeDialog");
});

test("edit follower and close subtype dialog", async () => {
    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv["res.partner"].create([{}, {}]);
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: "res.partner",
    });
    await start({
        async mockRPC(route, args) {
            if (route.includes("/mail/read_subscription_data")) {
                step("fetch_subtypes");
            }
        },
    });
    await openFormView("res.partner", threadId);
    await click(".o-mail-Followers-button");
    await contains(".o-mail-Follower");
    await contains("button[title='Edit subscription']");

    await click("button[title='Edit subscription']");
    await contains(".o-mail-FollowerSubtypeDialog");
    await assertSteps(["fetch_subtypes"]);

    await click(".o-mail-FollowerSubtypeDialog button", { text: "Cancel" });
    await contains(".o-mail-FollowerSubtypeDialog", { count: 0 });
});

test("remove a follower in a dirty form view", async () => {
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
                <field name="channel_ids" widget="many2many_tags"/>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                    <field name="message_follower_ids"/>
                </div>
            </form>`,
    };
    await start({ serverData: { views } });
    await openFormView("res.partner", threadId);
    await click(".o_field_many2many_tags[name='channel_ids'] input");
    await click(".dropdown-item", { text: "General" });
    await contains(".o_tag", { text: "General" });
    await contains(".o-mail-Followers-counter", { text: "1" });
    await editInput(document.body, ".o_field_char[name=name] input", "some value");
    await click(".o-mail-Followers-button");
    await click("button[title='Remove this follower']");
    await contains(".o-mail-Followers-counter", { text: "0" });
    await contains(".o_field_char[name=name] input", { value: "some value" });
    await contains(".o_tag", { text: "General" });
});

test("removing a follower should reload form view", async function () {
    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv["res.partner"].create([{}, {}]);
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: "res.partner",
    });
    await start({
        async mockRPC(route, args) {
            if (args.method === "web_read") {
                step(`read ${args.args[0][0]}`);
            }
        },
    });
    await openFormView("res.partner", threadId);
    await contains(".o-mail-Followers-button");
    await assertSteps([`read ${threadId}`]);
    await click(".o-mail-Followers-button");
    await click("button[title='Remove this follower']");
    await contains(".o-mail-Followers-counter", { text: "0" });
    await assertSteps([`read ${threadId}`]);
});
