/* @odoo-module */

import { afterNextRender, click, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("follow button");

QUnit.test("base rendering not editable", async (assert) => {
    const { openView, pyEnv } = await start();
    await openView({
        res_id: pyEnv.currentPartnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce(document.body, ".o-mail-Chatter-follow");
});

QUnit.test("hover following button", async (assert) => {
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
    assert.containsOnce(document.body, "button:contains(Following)");
    assert.containsNone(document.body, ".fa-times + span:contains(Following)");
    assert.containsOnce(document.body, ".fa-check + span:contains(Following)");

    await afterNextRender(() => {
        $("button:contains(Following)")[0].dispatchEvent(new window.MouseEvent("mouseenter"));
    });
    assert.containsOnce(document.body, "button:contains(Unfollow)");
    assert.containsOnce(document.body, ".fa-times + span:contains(Unfollow)");
    assert.containsNone(document.body, ".fa-check + span:contains(Unfollow)");
});

QUnit.test('click on "follow" button', async (assert) => {
    const { openView, pyEnv } = await start();
    await openView({
        res_id: pyEnv.currentPartnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce(document.body, "button:contains(Follow)");

    await click("button:contains(Follow)");
    assert.containsOnce(document.body, "button:contains(Following)");
});

QUnit.test('Click on "follow" button should save draft record', async (assert) => {
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
    await openFormView("res.partner");
    assert.containsOnce(document.body, "button:contains(Follow)");
    assert.containsOnce(document.body, "div.o_field_char");

    await click("button:contains(Follow)");
    assert.containsOnce(document.body, "div.o_field_invalid");
});

QUnit.test('click on "unfollow" button', async (assert) => {
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
    assert.containsOnce(document.body, "button:contains(Following)");

    await click("button:contains(Following)");
    assert.containsOnce(document.body, "button:contains(Follow)");
});
