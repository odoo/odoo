/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains, triggerEvents } from "@web/../tests/utils";

QUnit.module("follow button");

QUnit.test("base rendering not editable", async () => {
    const { openView, pyEnv } = await start();
    openView({
        res_id: pyEnv.currentPartnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains(".o-mail-Chatter-follow");
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
    openView({
        res_id: threadId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains(".fa-check + span", { text: "Following" });
    await contains(".fa-times + span", { count: 0, text: "Following" });
    await triggerEvents("button .fa-check + span", ["mouseenter"], { text: "Following" });
    await contains(".fa-times + span", { text: "Unfollow" });
    await contains(".fa-check + span", { count: 0, text: "Unfollow" });
});

QUnit.test('click on "follow" button', async () => {
    const { openView, pyEnv } = await start();
    openView({
        res_id: pyEnv.currentPartnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
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
    const { openFormView } = await start({ serverData: { views } });
    openFormView("res.partner");
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
    openView({
        res_id: threadId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await click(".fa-check + span", { text: "Following" });
    await contains("button", { text: "Follow" });
});
