import { describe, expect, test } from "@odoo/hoot";
import {
    assertSteps,
    click,
    contains,
    defineMailModels,
    editInput,
    onRpcBefore,
    openFormView,
    start,
    startServer,
    step,
} from "../../mail_test_helpers";
import { mockService, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { Deferred } from "@odoo/hoot-mock";
import { MailThread } from "../../mock_server/mock_models/mail_thread";
import { getMockEnv } from "@web/../tests/_framework/env_test_helpers";
import { actionService } from "@web/webclient/actions/action_service";

describe.current.tags("desktop");
defineMailModels();

test("base rendering not editable", async () => {
    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv["res.partner"].create([{}, {}]);
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: "res.partner",
    });
    patchWithCleanup(MailThread.prototype, {
        _get_mail_thread_data() {
            // mimic user without write access
            const res = super._get_mail_thread_data(...arguments);
            res["hasWriteAccess"] = false;
            return res;
        },
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
    await contains("button[title='Edit subscription']");
    await contains("button[title='Remove this follower']");
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
    mockService("action", () => {
        const ogService = actionService.start(getMockEnv());
        return {
            ...ogService,
            doAction(action) {
                if (action?.res_id === partnerId) {
                    step("do_action");
                    expect(action.res_id).toBe(partnerId);
                    expect(action.res_model).toBe("res.partner");
                    expect(action.type).toBe("ir.actions.act_window");
                    openFormDef.resolve();
                    return;
                }
                return ogService.doAction.call(this, ...arguments);
            },
        };
    });
    await start();
    await openFormView("res.partner", threadId);
    await click(".o-mail-Followers-button");
    await contains(".o-mail-Follower");
    await contains(".o-mail-Follower-details");
    $(".o-mail-Follower-details")[0].click();
    await openFormDef;
    await assertSteps(["do_action"]); // redirect to partner profile
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
    onRpcBefore("/mail/read_subscription_data", () => step("fetch_subtypes"));
    await start();
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
    onRpcBefore("/mail/read_subscription_data", () => step("fetch_subtypes"));
    await start();
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
    onRpc("res.partner", "web_read", ({ args }) => step(`read ${args[0][0]}`));
    await start();
    await openFormView("res.partner", threadId);
    await contains(".o-mail-Followers-button");
    await assertSteps([`read ${threadId}`]);
    await click(".o-mail-Followers-button");
    await click("button[title='Remove this follower']");
    await contains(".o-mail-Followers-counter", { text: "0" });
    await assertSteps([`read ${threadId}`]);
});
