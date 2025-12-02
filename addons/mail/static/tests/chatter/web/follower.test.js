import {
    click,
    contains,
    defineMailModels,
    editInput,
    onRpcBefore,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { Deferred } from "@odoo/hoot-mock";
import { asyncStep, mockService, onRpc, waitForSteps } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("base rendering not editable", async () => {
    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv["res.partner"].create([
        { hasWriteAccess: false },
        { hasWriteAccess: false },
    ]);
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
    await contains("[title='Edit subscription']");
    await contains("[title='Remove this follower']");
});

test("click on partner follower details", async () => {
    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv["res.partner"].create([{}, {}]);
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: "res.partner",
    });
    const openFormDef = new Deferred();
    mockService("action", {
        doAction(action) {
            if (action?.res_id !== partnerId) {
                return super.doAction(...arguments);
            }
            asyncStep("do_action");
            expect(action.res_id).toBe(partnerId);
            expect(action.res_model).toBe("res.partner");
            expect(action.type).toBe("ir.actions.act_window");
            openFormDef.resolve();
        },
    });
    await start();
    await openFormView("res.partner", threadId);
    await click(".o-mail-Followers-button");
    await contains(".o-mail-Follower");
    await contains(".o-mail-Follower-details");
    await click(".o-mail-Follower-details:first");
    await openFormDef;
    await waitForSteps(["do_action"]); // redirect to partner profile
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
    onRpcBefore("/mail/read_subscription_data", () => asyncStep("fetch_subtypes"));
    await start();
    await openFormView("res.partner", threadId);
    await click(".o-mail-Followers-button");
    await contains(".o-mail-Follower");
    await contains("[title='Edit subscription']");
    await click("[title='Edit subscription']");
    await contains(".o-mail-Follower", { count: 0 });
    await waitForSteps(["fetch_subtypes"]);
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
    onRpcBefore("/mail/read_subscription_data", () => asyncStep("fetch_subtypes"));
    await start();
    await openFormView("res.partner", threadId);
    await click(".o-mail-Followers-button");
    await contains(".o-mail-Follower");
    await contains("[title='Edit subscription']");
    await click("[title='Edit subscription']");
    await contains(".o-mail-FollowerSubtypeDialog");
    await waitForSteps(["fetch_subtypes"]);
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
    await start();
    await openFormView("res.partner", threadId, {
        arch: `
            <form>
                <field name="name"/>
                <field name="channel_ids" widget="many2many_tags"/>
                <chatter/>
            </form>`,
    });
    await click(".o_field_many2many_tags[name='channel_ids'] input");
    await click(".dropdown-item", { text: "General" });
    await contains(".o_tag", { text: "General" });
    await contains(".o-mail-Followers-counter", { text: "1" });
    await editInput(document.body, ".o_field_char[name=name] input", "some value");
    await click(".o-mail-Followers-button");
    await click("[title='Remove this follower']");
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
    onRpc("res.partner", "web_read", ({ args }) => asyncStep(`read ${args[0][0]}`));
    await start();
    await openFormView("res.partner", threadId);
    await contains(".o-mail-Followers-button");
    await waitForSteps([`read ${threadId}`]);
    await click(".o-mail-Followers-button");
    await click("[title='Remove this follower']");
    await contains(".o-mail-Followers-counter", { text: "0" });
    await waitForSteps([`read ${threadId}`]);
});
