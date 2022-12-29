/** @odoo-module **/

import { afterNextRender, click, start, startServer } from "@mail/../tests/helpers/test_utils";
import { getFixture } from "@web/../tests/helpers/utils";

let target;
QUnit.module("follow button", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("base rendering not editable", async function (assert) {
    const { openView, pyEnv } = await start();
    await openView({
        res_id: pyEnv.currentPartnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce(target, ".o-mail-chatter-topbar-follow");
});

QUnit.test("hover following button", async function (assert) {
    const pyEnv = await startServer();
    const threadId = pyEnv["res.partner"].create({});
    const followerId = pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: pyEnv.currentPartnerId,
        res_id: threadId,
        res_model: "res.partner",
    });
    pyEnv["res.partner"].write([pyEnv.currentPartnerId], {
        message_follower_ids: [followerId],
    });
    const { openView } = await start();
    await openView({
        res_id: threadId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce(target, "button:contains(Following)");
    assert.containsNone(target, ".fa-times + span:contains(Following)");
    assert.containsOnce(target, ".fa-check + span:contains(Following)");

    await afterNextRender(() => {
        $("button:contains(Following)")[0].dispatchEvent(new window.MouseEvent("mouseenter"));
    });
    assert.containsOnce(target, "button:contains(Unfollow)");
    assert.containsOnce(target, ".fa-times + span:contains(Unfollow)");
    assert.containsNone(target, ".fa-check + span:contains(Unfollow)");
});

QUnit.test('click on "follow" button', async function (assert) {
    const { openView, pyEnv } = await start();
    await openView({
        res_id: pyEnv.currentPartnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce(target, "button:contains(Follow)");

    await click("button:contains(Follow)");
    assert.containsOnce(target, "button:contains(Following)");
});

QUnit.test('click on "unfollow" button', async function (assert) {
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
    assert.containsOnce(target, "button:contains(Following)");

    await click("button:contains(Following)");
    assert.containsOnce(target, "button:contains(Follow)");
});
