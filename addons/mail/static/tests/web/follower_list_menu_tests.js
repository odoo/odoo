/* @odoo-module */

import { afterNextRender, click, start, startServer } from "@mail/../tests/helpers/test_utils";

import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { nextTick } from "web.test_utils";

QUnit.module("follower list menu");

QUnit.test("base rendering not editable", async (assert) => {
    const { openView } = await start();
    await openView(
        {
            res_model: "res.partner",
            views: [[false, "form"]],
        },
        { mode: "edit" }
    );
    assert.containsOnce($, ".o-mail-Followers");
    assert.containsOnce($, ".o-mail-Followers-button");
    assert.ok($(".o-mail-Followers-button")[0].disabled);
    assert.containsNone($, ".o-mail-Followers-dropdown");

    $(".o-mail-Followers-button")[0].click();
    await nextTick();
    assert.containsNone($, ".o-mail-Followers-dropdown");
});

QUnit.test("base rendering editable", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openView } = await start({
        async mockRPC(route, args, performRPC) {
            if (route === "/mail/thread/data") {
                // mimic user with write access
                const res = await performRPC(route, args);
                res["hasWriteAccess"] = true;
                return res;
            }
        },
    });
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-mail-Followers");
    assert.containsOnce($, ".o-mail-Followers-button");
    assert.notOk($(".o-mail-Followers-button")[0].disabled);
    assert.containsNone($, ".o-mail-Followers-dropdown");

    await click(".o-mail-Followers-button");
    assert.containsOnce($, ".o-mail-Followers-dropdown");
});

QUnit.test('click on "add followers" button', async (assert) => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2, partnerId_3] = pyEnv["res.partner"].create([
        { name: "Partner1" },
        { name: "François Perusse" },
        { name: "Partner3" },
    ]);
    pyEnv["mail.followers"].create({
        partner_id: partnerId_2,
        email: "bla@bla.bla",
        is_active: true,
        res_id: partnerId_1,
        res_model: "res.partner",
    });

    const { env, openView } = await start({
        async mockRPC(route, args, performRPC) {
            if (route === "/mail/thread/data") {
                // mimic user with write access
                const res = await performRPC(route, args);
                res["hasWriteAccess"] = true;
                return res;
            }
        },
    });
    await openView({
        res_id: partnerId_1,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            assert.step("action:open_view");
            assert.strictEqual(action.context.default_res_model, "res.partner");
            assert.strictEqual(action.context.default_res_id, partnerId_1);
            assert.strictEqual(action.res_model, "mail.wizard.invite");
            assert.strictEqual(action.type, "ir.actions.act_window");
            pyEnv["mail.followers"].create({
                partner_id: partnerId_3,
                email: "bla@bla.bla",
                is_active: true,
                name: "Wololo",
                res_id: partnerId_1,
                res_model: "res.partner",
            });
            options.onClose();
        },
    });

    assert.containsOnce($, ".o-mail-Followers");
    assert.containsOnce($, ".o-mail-Followers-button");
    assert.strictEqual($(".o-mail-Followers-counter").text(), "1");

    await click(".o-mail-Followers-button");
    assert.containsOnce($, ".o-mail-Followers-dropdown");
    assert.containsOnce($, "a:contains(Add Followers)");

    await click("a:contains(Add Followers)");
    assert.containsNone($, ".o-mail-Followers-dropdown");
    assert.verifySteps(["action:open_view"]);
    assert.strictEqual($(".o-mail-Followers-counter").text(), "2");

    await click(".o-mail-Followers-button");
    assert.containsN($, ".o-mail-Follower", 2);
    assert.strictEqual($(".o-mail-Follower").text(), "François PerussePartner3");
});

QUnit.test("click on remove follower", async (assert) => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "Partner1" },
        { name: "Partner2" },
    ]);
    pyEnv["mail.followers"].create({
        partner_id: partnerId_2,
        email: "bla@bla.bla",
        is_active: true,
        name: "Wololo",
        res_id: partnerId_1,
        res_model: "res.partner",
    });
    const { openView } = await start({
        async mockRPC(route, args, performRPC) {
            if (route === "/mail/thread/data") {
                // mimic user with write access
                const res = await performRPC(route, args);
                res["hasWriteAccess"] = true;
                return res;
            }
            if (route.includes("message_unsubscribe")) {
                assert.step("message_unsubscribe");
                assert.deepEqual(args.args, [[partnerId_1], [partnerId_2]]);
            }
        },
    });
    await openView({
        res_id: partnerId_1,
        res_model: "res.partner",
        views: [[false, "form"]],
    });

    await click(".o-mail-Followers-button");
    assert.containsOnce($, ".o-mail-Follower");
    assert.containsOnce($, "button[title='Remove this follower']");

    await click("button[title='Remove this follower']");
    assert.verifySteps(["message_unsubscribe"]);
    assert.containsNone($, ".o-mail-Follower");
});

QUnit.test(
    'Hide "Add follower" and subtypes edition/removal buttons except own user on read only record',
    async (assert) => {
        const pyEnv = await startServer();
        const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
            { name: "Partner1" },
            { name: "Partner2" },
        ]);
        pyEnv["mail.followers"].create([
            {
                is_active: true,
                partner_id: pyEnv.currentPartnerId,
                res_id: partnerId_1,
                res_model: "res.partner",
            },
            {
                is_active: true,
                partner_id: partnerId_2,
                res_id: partnerId_1,
                res_model: "res.partner",
            },
        ]);
        const { openView } = await start({
            async mockRPC(route, args, performRPC) {
                if (route === "/mail/thread/data") {
                    // mimic user with no write access
                    const res = await performRPC(route, args);
                    res["hasWriteAccess"] = false;
                    return res;
                }
            },
        });
        await openView({
            res_id: partnerId_1,
            res_model: "res.partner",
            views: [[false, "form"]],
        });

        await click(".o-mail-Followers-button");
        assert.containsNone($, "a:contains(Add Followers)");
        const $followers = $(".o-mail-Follower");
        assert.containsOnce($followers[0], "button[title='Edit subscription']");
        assert.containsOnce($followers[0], "button[title='Remove this follower']");
        assert.containsNone($followers[1], "button[title='Edit subscription']");
        assert.containsNone($followers[1], "button[title='Remove this follower']");
    }
);

QUnit.test("Load 100 followers at once", async (assert) => {
    const pyEnv = await startServer();
    const partnerIds = pyEnv["res.partner"].create(
        [...Array(210).keys()].map((i) => ({ display_name: `Partner${i}`, name: `Partner${i}` }))
    );
    pyEnv["mail.followers"].create(
        [...Array(210).keys()].map((i) => {
            return {
                is_active: true,
                partner_id: i === 0 ? pyEnv.currentPartnerId : partnerIds[i],
                res_id: partnerIds[0],
                res_model: "res.partner",
            };
        })
    );
    const { openFormView } = await start();
    await openFormView("res.partner", partnerIds[0]);
    assert.containsOnce($, "button[title='Show Followers']:contains(210)");

    await click("button[title='Show Followers']");
    assert.containsOnce($, ".o-mail-Follower:contains(Mitchell Admin)");
    assert.containsN($, ".o-mail-Follower", 100);
    assert.containsOnce($, ".o-mail-Followers-dropdown span:contains(Load more)");
    await afterNextRender(() =>
        $(".o-mail-Followers-dropdown span:contains(Load more)")[0].scrollIntoView()
    );
    assert.containsN($, ".o-mail-Follower", 200);
    assert.containsOnce($, ".o-mail-Followers-dropdown span:contains(Load more)");
    await afterNextRender(() =>
        $(".o-mail-Followers-dropdown span:contains(Load more)")[0].scrollIntoView()
    );
    assert.containsN($, ".o-mail-Follower", 210);
    assert.containsNone($, ".o-mail-Followers-dropdown span:contains(Load more)");
});

QUnit.test("Load 100 recipients at once", async (assert) => {
    const pyEnv = await startServer();
    const partnerIds = pyEnv["res.partner"].create(
        [...Array(210).keys()].map((i) => ({
            display_name: `Partner${i}`,
            name: `Partner${i}`,
            email: `partner${i}@example.com`,
        }))
    );
    pyEnv["mail.followers"].create(
        [...Array(210).keys()].map((i) => {
            return {
                is_active: true,
                partner_id: i === 0 ? pyEnv.currentPartnerId : partnerIds[i],
                res_id: partnerIds[0],
                res_model: "res.partner",
            };
        })
    );
    const { openFormView } = await start();
    await openFormView("res.partner", partnerIds[0]);
    assert.containsOnce($, "button[title='Show Followers']:contains(210)");
    await click("button:contains(Send message)");
    assert.containsOnce(
        $,
        ".o-mail-Chatter:contains('me, partner1, partner2, partner3, partner4, …')"
    );
    assert.containsOnce($, "button[title='Show all recipients']");
    await click("button[title='Show all recipients']");
    assert.containsN($, ".o-mail-RecipientList li", 100);
    assert.containsOnce($, ".o-mail-RecipientList span:contains(Load more)");
    await afterNextRender(() =>
        $(".o-mail-RecipientList span:contains(Load more)")[0].scrollIntoView()
    );
    assert.containsN($, ".o-mail-RecipientList li", 200);
    assert.containsOnce($, ".o-mail-RecipientList span:contains(Load more)");
    await afterNextRender(() =>
        $(".o-mail-RecipientList span:contains(Load more)")[0].scrollIntoView()
    );
    assert.containsN($, ".o-mail-RecipientList li", 210);
    assert.containsNone($, ".o-mail-RecipientList span:contains(Load more)");
});

QUnit.test(
    'Show "Add follower" and subtypes edition/removal buttons on all followers if user has write access',
    async (assert) => {
        const pyEnv = await startServer();
        const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
            { name: "Partner1" },
            { name: "Partner2" },
        ]);
        pyEnv["mail.followers"].create([
            {
                is_active: true,
                partner_id: pyEnv.currentPartnerId,
                res_id: partnerId_1,
                res_model: "res.partner",
            },
            {
                is_active: true,
                partner_id: partnerId_2,
                res_id: partnerId_1,
                res_model: "res.partner",
            },
        ]);
        const { openView } = await start({
            async mockRPC(route, args, performRPC) {
                if (route === "/mail/thread/data") {
                    // mimic user with write access
                    const res = await performRPC(...arguments);
                    res["hasWriteAccess"] = true;
                    return res;
                }
            },
        });
        await openView({
            res_id: partnerId_1,
            res_model: "res.partner",
            views: [[false, "form"]],
        });

        await click(".o-mail-Followers-button");
        assert.containsOnce($, "a:contains(Add Followers)");
        const $followers = $(".o-mail-Follower");
        assert.containsOnce($followers[0], "button[title='Edit subscription']");
        assert.containsOnce($followers[0], "button[title='Remove this follower']");
        assert.containsOnce($followers[1], "button[title='Edit subscription']");
        assert.containsOnce($followers[1], "button[title='Remove this follower']");
    }
);

QUnit.test(
    'Show "No Followers" dropdown-item if there are no followers and user does not have write access',
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({});
        const { openView } = await start({
            async mockRPC(route, args, performRPC) {
                if (route === "/mail/thread/data") {
                    // mimic user without write access
                    const res = await performRPC(route, args);
                    res["hasWriteAccess"] = false;
                    return res;
                }
            },
        });
        await openView({
            res_id: partnerId,
            res_model: "res.partner",
            views: [[false, "form"]],
        });

        await click(".o-mail-Followers-button");
        assert.containsOnce($, "div:contains(No Followers).disabled");
    }
);
