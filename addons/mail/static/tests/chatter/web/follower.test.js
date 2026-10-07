import {
    click,
    contains as mailContains,
    defineMailModels,
    editInput,
    onRpcBefore,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test, waitFor, waitForNone } from "@odoo/hoot";
import { contains, onRpc } from "@web/../tests/web_test_helpers";

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
    await waitFor(".o-mail-Follower:count(1)");
    await waitFor(".o-mail-Follower-details:count(1)");
    await waitFor(".o-mail-Follower-avatar:count(1)");
    await waitForNone(".o-mail-Follower-action");
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
    await waitFor(".o-mail-Follower:count(1)");
    await waitFor(".o-mail-Follower-details:count(1)");
    await waitFor(".o-mail-Follower-avatar:count(1)");
    await waitFor(".o-mail-Follower:count(1)");
    await waitFor("[title='Edit Notification Preferences']:count(1)");
    await waitFor("[title='Remove this follower']:count(1)");
});

test("click on partner follower opens avatar card", async () => {
    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv["res.partner"].create([{}, { name: "Batman" }]);
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", threadId);
    await click(".o-mail-Followers-button");
    await waitFor(".o-mail-Follower:count(1)");
    await waitFor(".o-mail-Follower-details:count(1)");
    await click(".o-mail-Follower-details:first");
    await waitFor(".o_avatar_card:contains('Batman'):count(1)");
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
    onRpcBefore("/mail/read_subscription_data", () => expect.step("fetch_subtypes"));
    await start();
    await openFormView("res.partner", threadId);
    await click(".o-mail-Followers-button");
    await waitFor(".o-mail-Follower:count(1)");
    await waitFor("[title='Edit Notification Preferences']:count(1)");
    await click("[title='Edit Notification Preferences']");
    await waitForNone(".o-mail-Follower");
    await expect.waitForSteps(["fetch_subtypes"]);
    await waitFor(".o-mail-FollowerSubtypeDialog:count(1)");
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
    onRpcBefore("/mail/read_subscription_data", () => expect.step("fetch_subtypes"));
    await start();
    await openFormView("res.partner", threadId);
    await contains(".o-mail-Followers-button:enabled:count(1)").click();
    await waitFor(".o-mail-Follower:count(1)");
    await waitFor("[title='Edit Notification Preferences']:count(1)");
    await contains("[title='Edit Notification Preferences']:count(1)").click();
    await waitFor(".o-mail-FollowerSubtypeDialog:count(1)");
    await expect.waitForSteps(["fetch_subtypes"]);
    await contains(".o-mail-FollowerSubtypeDialog button:text('Discard'):count(1)").click();
    await waitForNone(".o-mail-FollowerSubtypeDialog");
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
    await contains(".o_field_many2many_tags[name='channel_ids'] input:count(1)").click();
    await contains(".dropdown-item:text('General'):count(1)").click();
    await waitFor(".o_tag:text('General'):count(1)");
    await waitFor(".o-mail-Followers-counter:text('1'):count(1)");
    await editInput(document.body, ".o_field_char[name=name] input", "some value");
    await contains(".o-mail-Followers-button:enabled:count(1)").click();
    await contains("[title='Remove this follower']:count(1)").click();
    await waitFor(".o-mail-Followers-counter:text('0'):count(1)");
    await mailContains(".o_field_char[name=name] input", { value: "some value" });
    await waitFor(".o_tag:text('General'):count(1)");
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
    onRpc("res.partner", "web_read", ({ args }) => expect.step(`read ${args[0][0]}`));
    await start();
    await openFormView("res.partner", threadId);
    await waitFor(".o-mail-Followers-button:count(1)");
    await expect.waitForSteps([`read ${threadId}`]);
    await contains(".o-mail-Followers-button:enabled:count(1)").click();
    await contains("[title='Remove this follower']:count(1)").click();
    await waitFor(".o-mail-Followers-counter:text('0'):count(1)");
    await expect.waitForSteps([`read ${threadId}`]);
});
