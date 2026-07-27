import {
    click,
    contains,
    defineMailModels,
    openFormView,
    scroll,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

import { describe, expect, test } from "@odoo/hoot";
import { tick, waitFor, waitForNone } from "@odoo/hoot-dom";
import { mockService, serverState } from "@web/../tests/web_test_helpers";
import { range } from "@web/core/utils/numbers";

describe.current.tags("desktop");
defineMailModels();

test("base rendering not editable", async () => {
    await start();
    await openFormView("res.partner", undefined, {});
    await waitFor(".o-mail-Followers:count(1)");
    await waitFor(".o-mail-Followers-button:disabled:count(1)");
    await waitForNone(".o-mail-Followers-dropdown");
    await click(".o-mail-Followers-button");
    await waitForNone(".o-mail-Followers-dropdown");
});

test("base rendering editable", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    await start();
    await openFormView("res.partner", partnerId);
    await waitFor(".o-mail-Followers:count(1)");
    await waitFor(".o-mail-Followers-button:count(1)");
    await waitFor(".o-mail-Followers-button:first:enabled:count(1)");
    await waitForNone(".o-mail-Followers-dropdown");
    await click(".o-mail-Followers-button");
    await waitFor(".o-mail-Followers-dropdown:count(1)");
});

test('click on "add followers" button', async () => {
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
    mockService("action", {
        doAction(action, options) {
            if (action?.res_model !== "mail.followers.edit") {
                return super.doAction(...arguments);
            }
            expect.step("action:open_view");
            expect(action.context.default_res_model).toBe("res.partner");
            expect(action.context.default_res_ids).toEqual([partnerId_1]);
            expect(action.res_model).toBe("mail.followers.edit");
            expect(action.type).toBe("ir.actions.act_window");
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
    await start();
    await openFormView("res.partner", partnerId_1);
    await waitFor(".o-mail-Followers:count(1)");
    await waitFor(".o-mail-Followers-counter:text('1'):count(1)");
    await click(".o-mail-Followers-button");
    await waitFor(".o-mail-Followers-dropdown:count(1)");
    await click("a:text('Add Followers')");
    await waitForNone(".o-mail-Followers-dropdown");
    await expect.waitForSteps(["action:open_view"]);
    await waitFor(".o-mail-Followers-counter:text('2'):count(1)");
    await click(".o-mail-Followers-button");
    await waitFor(".o-mail-Follower:count(2)");
    await waitFor(".o-mail-Follower:eq(0):text('François Perusse'):count(1)");
    await waitFor(".o-mail-Follower:eq(1):text('Partner3'):count(1)");
});

test("click on remove follower", async () => {
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
    await start();
    await openFormView("res.partner", partnerId_1);
    await click(".o-mail-Followers-button");
    await waitFor(".o-mail-Follower:count(1)");
    await click("[title='Remove this follower']");
    await waitForNone(".o-mail-Follower");
    await waitFor(".o-mail-Followers-dropdown:count(1)");
});

test("Load 20 followers at once", async () => {
    const pyEnv = await startServer();
    const partnerIds = pyEnv["res.partner"].create(
        range(60).map((i) => ({ display_name: `Partner${i}`, name: `Partner${i}` }))
    );
    pyEnv["mail.followers"].create(
        range(60).map((i) => ({
            is_active: true,
            partner_id: i === 0 ? serverState.partnerId : partnerIds[i],
            res_id: partnerIds[0],
            res_model: "res.partner",
        }))
    );
    await start();
    await openFormView("res.partner", partnerIds[0]);
    await click("button[title='Show Followers']:text('60')");
    await waitFor(".o-mail-Follower:count(20)");
    await waitFor(".o-mail-Followers-dropdown:has(:text('Load more')):count(1)");
    await scroll(".o-mail-Followers-dropdown", "bottom");
    await waitFor(".o-mail-Follower:count(40)");
    await tick(); // give enough time for the useVisible hook to register load more as hidden
    await scroll(".o-mail-Followers-dropdown", "bottom");
    await waitFor(".o-mail-Follower:count(59)");
    await waitForNone(".o-mail-Followers-dropdown:has(:text('Load more'))");
});

test("Load 100 recipients at once", async () => {
    const pyEnv = await startServer();
    const partnerIds = pyEnv["res.partner"].create(
        range(210).map((i) => ({
            display_name: `Partner${i}`,
            name: `Partner${i}`,
            email: `partner${i}@example.com`,
        }))
    );
    pyEnv["mail.followers"].create(
        range(210).map((i) => ({
            is_active: true,
            partner_id: i === 0 ? serverState.partnerId : partnerIds[i],
            res_id: partnerIds[0],
            res_model: "res.partner",
        }))
    );
    await start();
    await openFormView("res.partner", partnerIds[0]);
    await waitFor("button[title='Show Followers']:text('210'):count(1)");
});

test('Show "Add follower" and subtypes edition/removal buttons on all followers if user has write access', async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "Partner1" },
        { name: "Partner2" },
    ]);
    pyEnv["mail.followers"].create([
        {
            is_active: true,
            partner_id: serverState.partnerId,
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
    await start();
    await openFormView("res.partner", partnerId_1);
    await click(".o-mail-Followers-button");
    await waitFor("a:text('Add Followers'):count(1)");
    await contains(":nth-child(1 of .o-mail-Follower)", {
        contains: [["[title='Edit Notification Preferences']"], ["[title='Remove this follower']"]],
    });
});

test('Show "No Followers" dropdown-item if there are no followers and user does not have write access', async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ hasWriteAccess: false });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Followers-button");
    await waitFor("div.disabled:text('No Followers'):count(1)");
});
