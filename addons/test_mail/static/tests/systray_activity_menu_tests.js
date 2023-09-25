/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { date_to_str } from "@web/legacy/js/core/time";
import { session } from "@web/session";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { click, contains } from "@web/../tests/utils";

QUnit.module("activity menu");

QUnit.test("menu with no records", async () => {
    await start({
        async mockRPC(route, args) {
            if (args.method === "systray_get_activities") {
                return [];
            }
        },
    });
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Activities'])");
    await contains(".o-mail-ActivityMenu", {
        text: "Congratulations, you're done with your activities.",
    });
});

QUnit.test("do not show empty text when at least some future activities", async () => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const pyEnv = await startServer();
    const activityId = pyEnv["mail.test.activity"].create({});
    pyEnv["mail.activity"].create([
        {
            date_deadline: date_to_str(tomorrow),
            res_id: activityId,
            res_model: "mail.test.activity",
        },
    ]);
    await start();
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Activities'])");
    await contains(".o-mail-ActivityMenu", {
        count: 0,
        text: "Congratulations, you're done with your activities.",
    });
});

QUnit.test("activity menu widget: activity menu with 2 models", async (assert) => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const activityIds = pyEnv["mail.test.activity"].create([{}, {}, {}, {}]);
    pyEnv["mail.activity"].create([
        { res_id: partnerId, res_model: "res.partner" },
        { res_id: activityIds[0], res_model: "mail.test.activity" },
        {
            date_deadline: date_to_str(tomorrow),
            res_id: activityIds[1],
            res_model: "mail.test.activity",
        },
        {
            date_deadline: date_to_str(tomorrow),
            res_id: activityIds[2],
            res_model: "mail.test.activity",
        },
        {
            date_deadline: date_to_str(yesterday),
            res_id: activityIds[3],
            res_model: "mail.test.activity",
        },
    ]);
    const { env } = await start();
    await contains(".o_menu_systray i[aria-label='Activities']");
    await contains(".o-mail-ActivityMenu-counter");
    await contains(".o-mail-ActivityMenu-counter", { text: "5" });
    let context = {};
    patchWithCleanup(env.services.action, {
        doAction(action) {
            assert.deepEqual(action.context, context);
        },
    });
    context = {
        force_search_count: 1,
        search_default_activities_overdue: 1,
    };
    await click(".o_menu_systray i[aria-label='Activities']");
    await contains(".o-mail-ActivityMenu");
    await contains(".o-mail-ActivityMenu .o-mail-ActivityGroup", { count: 2 });
    await click(".o-mail-ActivityMenu .o-mail-ActivityGroup button", { text: "1 Late" });
    await contains(".o-mail-ActivityMenu", { count: 0 });
    context = {
        force_search_count: 1,
        search_default_activities_today: 1,
    };
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Activities'])");
    await click(":nth-child(1 of .o-mail-ActivityGroup) button", { text: "1 Today" });
    await contains(".o-mail-ActivityMenu", { count: 0 });
    context = {
        force_search_count: 1,
        search_default_activities_upcoming_all: 1,
    };
    await click(".o_menu_systray i[aria-label='Activities']");
    await click(".o-mail-ActivityMenu .o-mail-ActivityGroup button", { text: "2 Future" });
    await contains(".o-mail-ActivityMenu", { count: 0 });
    context = {
        force_search_count: 1,
        search_default_activities_overdue: 1,
        search_default_activities_today: 1,
    };
    await click(".o_menu_systray i[aria-label='Activities']");
    await click(".o-mail-ActivityMenu .o-mail-ActivityGroup", { text: "mail.test.activity" });
    await contains(".o-mail-ActivityMenu", { count: 0 });
});

QUnit.test("activity menu widget: activity view icon", async (assert) => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const activityIds = pyEnv["mail.test.activity"].create([{}, {}, {}, {}]);
    pyEnv["mail.activity"].create([
        { res_id: partnerId, res_model: "res.partner" },
        { res_id: activityIds[0], res_model: "mail.test.activity" },
        {
            date_deadline: date_to_str(tomorrow),
            res_id: activityIds[1],
            res_model: "mail.test.activity",
        },
        {
            date_deadline: date_to_str(tomorrow),
            res_id: activityIds[2],
            res_model: "mail.test.activity",
        },
        {
            date_deadline: date_to_str(yesterday),
            res_id: activityIds[3],
            res_model: "mail.test.activity",
        },
    ]);
    const { env } = await start();
    await click(".o_menu_systray i[aria-label='Activities']");
    await contains("button[title='Summary']", { count: 2 });
    await contains(".o-mail-ActivityGroup", {
        text: "res.partner",
        contains: ["button[title='Summary'].fa-clock-o"],
    });
    await contains(".o-mail-ActivityGroup", {
        text: "mail.test.activity",
        contains: ["button[title='Summary'].fa-clock-o"],
    });
    await contains(".show .dropdown-menu");
    patchWithCleanup(env.services.action, {
        doAction(action) {
            if (action.name) {
                assert.ok(action.domain);
                assert.deepEqual(action.domain, [["activity_ids.user_id", "=", session.uid]]);
                assert.step("do_action:" + action.name);
            } else {
                assert.step("do_action:" + action);
            }
        },
    });
    await click("button[title='Summary']", {
        parent: [".o-mail-ActivityGroup", { text: "mail.test.activity" }],
    });
    await contains(".dropdown-menu", { count: 0 });
    await click(".o_menu_systray i[aria-label='Activities']");
    await click("button[title='Summary']", {
        parent: [".o-mail-ActivityGroup", { text: "res.partner" }],
    });
    assert.verifySteps(["do_action:mail.test.activity", "do_action:res.partner"]);
});

QUnit.test("activity menu widget: close on messaging menu click", async () => {
    await start();
    await click(".o_menu_systray i[aria-label='Activities']");
    await contains(".o-mail-ActivityMenu");
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-ActivityMenu", { count: 0 });
});
