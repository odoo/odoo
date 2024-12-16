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
import { tick } from "@odoo/hoot-dom";
import { asyncStep, mockService, serverState, waitForSteps } from "@web/../tests/web_test_helpers";

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
            asyncStep("action:open_view");
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
    await contains(".o-mail-Followers-counter", { text: "1" });
    await click(".o-mail-Followers-button");
    await contains(".o-mail-Followers-dropdown");
    await click("a", { text: "Add Followers" });
    await contains(".o-mail-Followers-dropdown", { count: 0 });
    await waitForSteps(["action:open_view"]);
    await contains(".o-mail-Followers-counter", { text: "2" });
    await click(".o-mail-Followers-button");
    await contains(".o-mail-Follower", { count: 2 });
    await contains(":nth-child(1 of .o-mail-Follower)", { text: "François Perusse" });
    await contains(":nth-child(2 of .o-mail-Follower)", { text: "Partner3" });
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
    await click("button[title='Remove this follower']");
    await contains(".o-mail-Follower", { count: 0 });
});

test('Hide "Add follower" and subtypes edition/removal buttons except own user on read only record', async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { hasWriteAccess: false, name: "Partner1" },
        { hasWriteAccess: false, name: "Partner2" },
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
    await contains("a", { count: 0, text: "Add Followers" });
    await contains(":nth-child(1 of .o-mail-Follower)", {
        contains: [["button[title='Edit subscription']"], ["button[title='Remove this follower']"]],
    });
    await contains(":nth-child(2 of .o-mail-Follower)", {
        contains: [
            ["button[title='Edit subscription']", { count: 0 }],
            ["button[title='Remove this follower']", { count: 0 }],
        ],
    });
});

test("Load 100 followers at once", async () => {
    const pyEnv = await startServer();
    const partnerIds = pyEnv["res.partner"].create(
        [...Array(210).keys()].map((i) => ({ display_name: `Partner${i}`, name: `Partner${i}` }))
    );
    pyEnv["mail.followers"].create(
        [...Array(210).keys()].map((i) => ({
            is_active: true,
            partner_id: i === 0 ? serverState.partnerId : partnerIds[i],
            res_id: partnerIds[0],
            res_model: "res.partner",
        }))
    );
    await start();
    await openFormView("res.partner", partnerIds[0]);
    await contains("button[title='Show Followers']", { text: "210" });
    await click("button[title='Show Followers']");
    await contains(".o-mail-Follower", { text: "Mitchell Admin" });
    await contains(".o-mail-Follower", { count: 101 }); // 100 more followers + self follower (Mitchell Admin)
    await contains(".o-mail-Followers-dropdown", { text: "Load more" });
    await scroll(".o-mail-Followers-dropdown", "bottom");
    await contains(".o-mail-Follower", { count: 201 });
    await tick(); // give enough time for the useVisible hook to register load more as hidden
    await scroll(".o-mail-Followers-dropdown", "bottom");
    await contains(".o-mail-Follower", { count: 210 });
    await contains(".o-mail-Followers-dropdown span", { count: 0, text: "Load more" });
});

test("Load 100 recipients at once", async () => {
    const pyEnv = await startServer();
    const partnerIds = pyEnv["res.partner"].create(
        [...Array(210).keys()].map((i) => ({
            display_name: `Partner${i}`,
            name: `Partner${i}`,
            email: `partner${i}@example.com`,
        }))
    );
    pyEnv["mail.followers"].create(
        [...Array(210).keys()].map((i) => ({
            is_active: true,
            partner_id: i === 0 ? serverState.partnerId : partnerIds[i],
            res_id: partnerIds[0],
            res_model: "res.partner",
        }))
    );
    await start();
    await openFormView("res.partner", partnerIds[0]);
    await contains("button[title='Show Followers']", { text: "210" });
    await click("button", { text: "Send message" });
    await click("button", { text: "Bcc" });
    await contains(".o-mail-Chatter", {
        text: "Bcc: Partner1, Partner2, Partner3, Partner4, Partner5, and 95 more",
    });
    await contains("button[title='Show all recipients']");
    await click("button[title='Show all recipients']");
    await contains(".o-mail-RecipientList li", { count: 100 });
    await contains(".o-mail-RecipientList", { text: "Load more" });
    await scroll(".o-mail-RecipientList", "bottom");
    await contains(".o-mail-RecipientList li", { count: 200 });
    await tick(); // give enough time for the useVisible hook to register load more as hidden
    await scroll(".o-mail-RecipientList", "bottom");
    await contains(".o-mail-RecipientList li", { count: 209 });
    await contains(".o-mail-RecipientList span", { count: 0, text: "Load more" });
});

test("Load recipient without email", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "Luigi" },
        { name: "Mario" },
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
    await click("button", { text: "Send message" });
    await click("button", { text: "Bcc" });
    await contains("span[title='no email address']", { text: "Mario" });
    await click("button[title='Show all recipients']");
    await contains(".o-mail-RecipientList li", { text: "Mario" });
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
    await contains("a", { text: "Add Followers" });
    await contains(":nth-child(1 of .o-mail-Follower)", {
        contains: [["button[title='Edit subscription']"], ["button[title='Remove this follower']"]],
    });
    await contains(":nth-child(2 of .o-mail-Follower)", {
        contains: [["button[title='Edit subscription']"], ["button[title='Remove this follower']"]],
    });
});

test('Show "No Followers" dropdown-item if there are no followers and user does not have write access', async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ hasWriteAccess: false });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Followers-button");
    await contains("div.disabled", { text: "No Followers" });
});
