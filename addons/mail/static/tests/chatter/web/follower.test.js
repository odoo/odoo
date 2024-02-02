/** @odoo-module */

import { expect, test } from "@odoo/hoot";
import {
    click,
    contains,
    editInput,
    openFormView,
    registerArchs,
    start,
    startServer,
} from "../../mail_test_helpers";
import { onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { Deferred } from "@odoo/hoot-mock";
import { MailThread } from "../../mock_server/mock_models/mail_thread";

test.skip("base rendering not editable", async () => {
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
            // mimic user with write access
            const res = super._get_mail_thread_data(...arguments);
            res["hasWriteAccess"] = true;
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

test.skip("base rendering editable", async () => {
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

test.skip("click on partner follower details", async () => {
    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv["res.partner"].create([{}, {}]);
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: "res.partner",
    });
    const openFormDef = new Deferred();
    const { env } = await start();
    await openFormView("res.partner", threadId);
    patchWithCleanup(env.services.action, {
        doAction(action) {
            expect.step("do_action");
            expect(action.res_id).toBe(partnerId);
            expect(action.res_model).toBe("res.partner");
            expect(action.type).toBe("ir.actions.act_window");
            openFormDef.resolve();
        },
    });
    await click(".o-mail-Followers-button");
    await contains(".o-mail-Follower");
    await contains(".o-mail-Follower-details");
    $(".o-mail-Follower-details")[0].click();
    await openFormDef;
    expect(["do_action"]).toVerifySteps({ message: "redirect to partner profile" });
});

test.skip("click on edit follower", async () => {
    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv["res.partner"].create([{}, {}]);
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: "res.partner",
    });
    onRpc((route) => {
        if (route === "/mail/read_subscription_data") {
            expect.step("fetch_subtypes");
        }
    });
    await start();
    await openFormView("res.partner", threadId);
    await click(".o-mail-Followers-button");
    await contains(".o-mail-Follower");
    await contains("button[title='Edit subscription']");
    await click("button[title='Edit subscription']");
    await contains(".o-mail-Follower", { count: 0 });
    expect(["fetch_subtypes"]).verifySteps();
    await contains(".o-mail-FollowerSubtypeDialog");
});

test.skip("edit follower and close subtype dialog", async () => {
    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv["res.partner"].create([{}, {}]);
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: "res.partner",
    });
    onRpc((route) => {
        if (route === "/mail/read_subscription_data") {
            expect.step("fetch_subtypes");
        }
    });
    await start();
    await openFormView("res.partner", threadId);
    await click(".o-mail-Followers-button");
    await contains(".o-mail-Follower");
    await contains("button[title='Edit subscription']");
    await click("button[title='Edit subscription']");
    await contains(".o-mail-FollowerSubtypeDialog");
    expect(["fetch_subtypes"]).verifySteps();
    await click(".o-mail-FollowerSubtypeDialog button", { text: "Cancel" });
    await contains(".o-mail-FollowerSubtypeDialog", { count: 0 });
});

test.skip("remove a follower in a dirty form view", async () => {
    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv["res.partner"].create([{}, {}]);
    pyEnv["discuss.channel"].create({ name: "General", display_name: "General" });
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: "res.partner",
    });
    registerArchs({
        "res.partner,false,form": `
            <form>
                <field name="name"/>
                <field name="channel_ids" widget="many2many_tags"/>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                    <field name="message_follower_ids"/>
                </div>
            </form>`,
    });
    await start();
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

test.skip("removing a follower should reload form view", async function () {
    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv["res.partner"].create([{}, {}]);
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: "res.partner",
    });
    onRpc((route, args) => {
        if (route === "/web/dataset/call_kw/res.partner/web_read") {
            expect.step(`read ${args.args[0][0]}`);
        }
    });
    await start();
    await openFormView("res.partner", threadId);
    await contains(".o-mail-Followers-button");
    expect([`read ${threadId}`]).toVerifySteps();
    await click(".o-mail-Followers-button");
    await click("button[title='Remove this follower']");
    await contains(".o-mail-Followers-counter", { text: "0" });
    expect([`read ${threadId}`]).toVerifySteps();
});
