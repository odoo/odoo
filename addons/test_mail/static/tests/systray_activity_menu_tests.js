/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { date_to_str } from "@web/legacy/js/core/time";
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
    await contains(
        ".o-mail-ActivityMenu:contains(Congratulations, you're done with your activities.)"
    );
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
    await contains(
        ".o-mail-ActivityMenu:contains(Congratulations, you're done with your activities.)",
        { count: 0 }
    );
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
    let actionChecks = {
        context: {
            force_search_count: 1,
            search_default_activities_my: true,
        },
    };
    patchWithCleanup(env.services.action, {
        doAction(action) {
            Object.entries(actionChecks).forEach(([key, value]) => {
                assert.deepEqual(action[key], value);
            });
            assert.step("do_action:" + action.name);
        },
    });
    await click(".o_menu_systray i[aria-label='Activities']");
    await contains(".o-mail-ActivityMenu");
    await contains(".o-mail-ActivityMenu .o-mail-ActivityGroup", { count: 2 });
    await contains(".o-mail-ActivityMenu .o-mail-ActivityGroup:contains('res.partner'):contains('0 Late')");
    await contains(".o-mail-ActivityMenu .o-mail-ActivityGroup:contains('res.partner'):contains('1 Today')");
    await contains(".o-mail-ActivityMenu .o-mail-ActivityGroup:contains('res.partner'):contains('0 Future')");
    await contains(".o-mail-ActivityMenu .o-mail-ActivityGroup:contains('mail.test.activity'):contains('1 Late')");
    await contains(".o-mail-ActivityMenu .o-mail-ActivityGroup:contains('mail.test.activity'):contains('1 Today')");
    await contains(".o-mail-ActivityMenu .o-mail-ActivityGroup:contains('mail.test.activity'):contains('2 Future')");
    actionChecks.res_model = 'res.partner';
    await click(".o-mail-ActivityMenu .o-mail-ActivityGroup:contains('res.partner')");
    await contains(".o-mail-ActivityMenu", { count: 0 });
    await click(".o_menu_systray i[aria-label='Activities']");
    actionChecks.res_model = 'mail.test.activity';
    await click(".o-mail-ActivityMenu .o-mail-ActivityGroup:contains('mail.test.activity')");
    assert.verifySteps(["do_action:res.partner", "do_action:mail.test.activity"]);
});

QUnit.test("activity menu widget: close on messaging menu click", async (assert) => {
    await start();
    await click(".o_menu_systray i[aria-label='Activities']");
    await contains(".o-mail-ActivityMenu");
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-ActivityMenu", { count: 0 });
});
