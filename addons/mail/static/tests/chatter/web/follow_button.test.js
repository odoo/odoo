/** @odoo-module alias=@mail/../tests/chatter/web/follow_button_tests default=false */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { openFormView, start } from "@mail/../tests/helpers/test_utils";

import { click, contains, triggerEvents } from "@web/../tests/utils";

QUnit.module("follow button");

QUnit.test("base rendering not editable", async () => {
    const { openView, pyEnv } = await start();
    await openView({
        res_id: pyEnv.currentPartnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains(".o-mail-Chatter-follow", { text: "Follow" });
});

QUnit.test("hover following button", async () => {
    const pyEnv = await startServer();
    const threadId = pyEnv["res.partner"].create({});
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: pyEnv.currentPartnerId,
        res_id: threadId,
        res_model: "res.partner",
    });
    const { openView } = await start();
    await openView({
        res_id: threadId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains(".o-mail-Chatter-follow", { text: "Following" });
    await triggerEvents(".o-mail-Chatter-follow", ["mouseenter"], { text: "Following" });
    await contains(".o-mail-Chatter-follow", { text: "Unfollow" });
});

QUnit.test('click on "follow" button', async () => {
    const { pyEnv } = await start();
    await openFormView("res.partner", pyEnv.currentPartnerId);
    await contains("button", { text: "Follow" });
    await click("button", { text: "Follow" });
    await contains("button", { text: "Following" });
});

QUnit.test('Click on "follow" button should save draft record', async () => {
    const views = {
        "res.partner,false,form": `
            <form string="Partners">
                <sheet>
                    <field name="name" required="1"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_follower_ids"/>
                </div>
            </form>`,
    };
    await start({ serverData: { views } });
    await openFormView("res.partner");
    await contains("button", { text: "Follow" });
    await contains("div.o_field_char");
    await click("button", { text: "Follow" });
    await contains("div.o_field_invalid");
});

QUnit.test('click on "unfollow" button', async () => {
    const pyEnv = await startServer();
    const threadId = pyEnv["res.partner"].create({});
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: pyEnv.currentPartnerId,
        res_id: threadId,
        res_model: "res.partner",
    });
    const { openView } = await start();
    await openView({
        res_id: threadId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await click(".o-mail-Chatter-follow", { text: "Following" });
    await contains("button", { text: "Follow" });
});
