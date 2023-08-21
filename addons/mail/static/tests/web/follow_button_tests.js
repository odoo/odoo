/* @odoo-module */

import { click, contains, start, startServer } from "@mail/../tests/helpers/test_utils";

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
    await contains("button:contains(Following)");
    await contains(".fa-times + span:contains(Following)", 0);
    await contains(".fa-check + span:contains(Following)");

    $("button:contains(Following)")[0].dispatchEvent(new window.MouseEvent("mouseenter"));
    await contains("button:contains(Unfollow)");
    await contains(".fa-times + span:contains(Unfollow)");
    await contains(".fa-check + span:contains(Unfollow)", 0);
});

QUnit.test('click on "follow" button', async () => {
    const { openView, pyEnv } = await start();
    openView({
        res_id: pyEnv.currentPartnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains("button:contains(Follow)");

    await click("button:contains(Follow)");
    await contains("button:contains(Following)");
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
    await contains("button:contains(Follow)");
    await contains("div.o_field_char");
    await click("button:contains(Follow)");
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
    await click("button:contains(Following)");
    await contains("button:contains(Follow)");
});
