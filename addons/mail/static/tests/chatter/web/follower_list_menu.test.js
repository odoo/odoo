import {
    click,
    contains,
    defineMailModels,
    insertText,
    openFormView,
    scroll,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

import { describe, expect, test } from "@odoo/hoot";
import { tick } from "@odoo/hoot-dom";
import { mockService, serverState } from "@web/../tests/web_test_helpers";
import { range } from "@web/core/utils/numbers";

describe.current.tags("desktop");
defineMailModels();

test("base rendering not editable", async () => {
    await start();
    await openFormView("res.partner", undefined, {});
    await contains(".o-mail-Followers");
    await contains(".o-mail-Followers-button:disabled");
    await contains(".o-mail-Followers-dropdown", { count: 0 });
    await click(".o-mail-Followers-button");
    await contains(".o-mail-Followers-dropdown", { count: 0 });
});

test("base rendering editable", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Followers");
    await contains(".o-mail-Followers-button");
    await contains(".o-mail-Followers-button:first:enabled");
    await contains(".o-mail-Followers-dropdown", { count: 0 });
    await click(".o-mail-Followers-button");
    await contains(".o-mail-Followers-dropdown");
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
    await contains(".o-mail-Followers");
    await contains(".o-mail-Followers-counter:text('1')");
    await click(".o-mail-Followers-button");
    await contains(".o-mail-Followers-dropdown");
    await click("button[title='Add Followers']:text('Add') [data-icon='person_add']");
    await contains(".o-mail-Followers-dropdown", { count: 0 });
    await expect.waitForSteps(["action:open_view"]);
    await contains(".o-mail-Followers-counter:text('2')");
    await click(".o-mail-Followers-button");
    await contains(".o-mail-Follower", { count: 2 });
    await contains(".o-mail-Follower:eq(0):text('François Perusse')");
    await contains(".o-mail-Follower:eq(1):text('Partner3')");
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
    await contains(".o-mail-Follower");
    await click("[title='Remove this follower']");
    await contains(".o-mail-Follower", { count: 0 });
    await contains(".o-mail-Followers-dropdown");
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
    await contains(".o-mail-Follower", { count: 20 });
    await contains(".o-mail-Followers-dropdown:has(:text('Load more'))");
    await scroll(".o-mail-Followers-dropdown", "bottom");
    await contains(".o-mail-Follower", { count: 40 });
    await tick(); // give enough time for the useVisible hook to register load more as hidden
    await scroll(".o-mail-Followers-dropdown", "bottom");
    await contains(".o-mail-Follower", { count: 59 });
    await contains(".o-mail-Followers-dropdown:has(:text('Load more'))", { count: 0 });
});

test("Search followers list by name or email", async () => {
    const pyEnv = await startServer();
    const partnerIds = pyEnv["res.partner"].create(
        range(21).map((i) => ({ email: `partner${i}@example.com`, name: `Partner${i}` }))
    );
    pyEnv["mail.followers"].create(
        partnerIds.map((partnerId) => ({
            partner_id: partnerId,
            res_id: partnerIds[0],
            res_model: "res.partner",
        }))
    );
    await start();
    await openFormView("res.partner", partnerIds[0]);
    // Search is visible when the thread has otherFollowersCount > 20 followers.
    await click("button[title='Show Followers']:text('21')");
    await contains(".o-mail-Follower", { count: 20 });
    await insertText("input[placeholder='Search by name or email']", "Partner9");
    await contains(".o-mail-Follower:text('Partner9')");
    await click("[title='Clear']");
    await contains(".o-mail-Follower:text('Partner9')", { count: 0 });
    await insertText("input[placeholder='Search by name or email']", "partner9@example.com");
    await contains(".o-mail-Follower:text('Partner9')");
    await click("[title='Clear']");
    await contains(".o-mail-Follower:text('Partner9')", { count: 0 });
    await insertText("input[placeholder='Search by name or email']", "Armstrong");
    await contains(".dropdown-item.disabled:text('No Matching Followers')");
    await click("[title='Clear']");
    // Search is hidden when the thread has otherFollowersCount <= 20 followers.
    await click(".o-mail-Follower:has(:text('Partner0')) [title='Remove this follower']");
    await contains("button[title='Show Followers']:text('20')");
    await contains(".o-mail-Follower", { count: 19 });
    await contains("input[placeholder='Search by name or email']", { count: 0 });
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
    await contains("button[title='Show Followers']:text('210')");
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
    await contains("button[title='Add Followers']:text('Add') [data-icon='person_add']");
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
    await contains("div.disabled:text('No Followers')");
});
