/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { click, contains, scroll } from "@web/../tests/utils";

QUnit.module("follower list menu");

QUnit.test("base rendering not editable", async () => {
    const { openView } = await start();
    openView(
        {
            res_model: "res.partner",
            views: [[false, "form"]],
        },
        { mode: "edit" }
    );
    await contains(".o-mail-Followers");
    await contains(".o-mail-Followers-button:disabled");
    await contains(".o-mail-Followers-dropdown", { count: 0 });
    await click(".o-mail-Followers-button");
    await contains(".o-mail-Followers-dropdown", { count: 0 });
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
    openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains(".o-mail-Followers");
    await contains(".o-mail-Followers-button");
    assert.notOk($(".o-mail-Followers-button")[0].disabled);
    await contains(".o-mail-Followers-dropdown", { count: 0 });

    await click(".o-mail-Followers-button");
    await contains(".o-mail-Followers-dropdown");
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
    openView({
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
    await contains(".o-mail-Followers");
    await contains(".o-mail-Followers-counter", { text: "1" });
    await click(".o-mail-Followers-button");
    await contains(".o-mail-Followers-dropdown");
    await click("a", { text: "Add Followers" });
    await contains(".o-mail-Followers-dropdown", { count: 0 });
    assert.verifySteps(["action:open_view"]);
    await contains(".o-mail-Followers-counter", { text: "2" });
    await click(".o-mail-Followers-button");
    await contains(".o-mail-Follower", { count: 2 });
    await contains(":nth-child(1 of .o-mail-Follower)", { text: "François Perusse" });
    await contains(":nth-child(2 of .o-mail-Follower)", { text: "Partner3" });
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
    openView({
        res_id: partnerId_1,
        res_model: "res.partner",
        views: [[false, "form"]],
    });

    await click(".o-mail-Followers-button");
    await contains(".o-mail-Follower");
    await contains("button[title='Remove this follower']");

    await click("button[title='Remove this follower']");
    assert.verifySteps(["message_unsubscribe"]);
    await contains(".o-mail-Follower", { count: 0 });
});

QUnit.test(
    'Hide "Add follower" and subtypes edition/removal buttons except own user on read only record',
    async () => {
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
        openView({
            res_id: partnerId_1,
            res_model: "res.partner",
            views: [[false, "form"]],
        });
        await click(".o-mail-Followers-button");
        await contains("a", { count: 0, text: "Add Followers" });
        await contains(":nth-child(1 of .o-mail-Follower)", {
            contains: [
                ["button[title='Edit subscription']"],
                ["button[title='Remove this follower']"],
            ],
        });
        await contains(":nth-child(2 of .o-mail-Follower)", {
            contains: [
                ["button[title='Edit subscription']", { count: 0 }],
                ["button[title='Remove this follower']", { count: 0 }],
            ],
        });
    }
);

QUnit.test("Load 100 followers at once", async () => {
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
    await contains("button[title='Show Followers']", { text: "210" });
    await click("button[title='Show Followers']");
    await contains(".o-mail-Follower", { text: "Mitchell Admin" });
    await contains(".o-mail-Follower", { count: 100 });
    await contains(".o-mail-Followers-dropdown", { text: "Load more" });
    await scroll(".o-mail-Followers-dropdown", "bottom");
    await contains(".o-mail-Follower", { count: 200 });
    await new Promise(setTimeout); // give enough time for the useVisible hook to register load more as hidden
    await scroll(".o-mail-Followers-dropdown", "bottom");
    await contains(".o-mail-Follower", { count: 210 });
    await contains(".o-mail-Followers-dropdown span", { count: 0, text: "Load more" });
});

QUnit.test("Load 100 recipients at once", async () => {
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
    await contains("button[title='Show Followers']", { text: "210" });
    await click("button", { text: "Send message" });
    await contains(".o-mail-Chatter", {
        text: "To: partner1, partner2, partner3, partner4, partner5, …",
    });
    await contains("button[title='Show all recipients']");
    await click("button[title='Show all recipients']");
    await contains(".o-mail-RecipientList li", { count: 100 });
    await contains(".o-mail-RecipientList", { text: "Load more" });
    await scroll(".o-mail-RecipientList", "bottom");
    await contains(".o-mail-RecipientList li", { count: 200 });
    await new Promise(setTimeout); // give enough time for the useVisible hook to register load more as hidden
    await scroll(".o-mail-RecipientList", "bottom");
    await contains(".o-mail-RecipientList li", { count: 209 });
    await contains(".o-mail-RecipientList span", { count: 0, text: "Load more" });
});

QUnit.test("Load recipient without email", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "Luigi" },
        { name: "Mario" },
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
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId_1);
    await click("button", { text: "Send message" });
    await contains("span[title='no email address']", { text: "Mario" });
    await click("button[title='Show all recipients']");
    await contains(".o-mail-RecipientList li", { text: "[Mario] (no email address)" });
});

QUnit.test(
    'Show "Add follower" and subtypes edition/removal buttons on all followers if user has write access',
    async () => {
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
        openView({
            res_id: partnerId_1,
            res_model: "res.partner",
            views: [[false, "form"]],
        });

        await click(".o-mail-Followers-button");
        await contains("a", { text: "Add Followers" });
        await contains(":nth-child(1 of .o-mail-Follower)", {
            contains: [
                ["button[title='Edit subscription']"],
                ["button[title='Remove this follower']"],
            ],
        });
        await contains(":nth-child(2 of .o-mail-Follower)", {
            contains: [
                ["button[title='Edit subscription']"],
                ["button[title='Remove this follower']"],
            ],
        });
    }
);

QUnit.test(
    'Show "No Followers" dropdown-item if there are no followers and user does not have write access',
    async () => {
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
        openView({
            res_id: partnerId,
            res_model: "res.partner",
            views: [[false, "form"]],
        });

        await click(".o-mail-Followers-button");
        await contains("div.disabled", { text: "No Followers" });
    }
);
