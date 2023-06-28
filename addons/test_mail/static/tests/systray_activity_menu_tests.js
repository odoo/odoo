/** @odoo-module **/

import { start, startServer, click } from "@mail/../tests/helpers/test_utils";

import { session } from "@web/session";
import { date_to_str } from "web.time";
import { patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module("activity menu");

QUnit.test("menu with no records", async (assert) => {
    await start({
        async mockRPC(route, args) {
            if (args.method === "systray_get_activities") {
                return [];
            }
        },
    });
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Activities'])");
    assert.containsOnce(
        $,
        ".o-mail-ActivityMenu:contains(Congratulations, you're done with your activities.)"
    );
});

QUnit.test("do not show empty text when at least some future activities", async (assert) => {
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
    assert.containsNone(
        $,
        ".o-mail-ActivityMenu:contains(Congratulations, you're done with your activities.)"
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
    assert.containsOnce($, ".o_menu_systray i[aria-label='Activities']");
    assert.containsOnce($, ".o-mail-ActivityMenu-counter");
    assert.containsOnce($, ".o-mail-ActivityMenu-counter:contains(5)");
    let actionChecks = {
        context: { force_search_count: 1 },
        domain: [["activity_ids.user_id", "=", session.uid]],
    }
    patchWithCleanup(env.services.action, {
        doAction(action) {
            Object.entries(actionChecks).forEach(([key, value]) => {
                assert.deepEqual(action[key], value);
            });
            assert.step("do_action:" + action.name);
        },
    });
    await click(".o_menu_systray i[aria-label='Activities']");
    assert.containsOnce($, ".o-mail-ActivityMenu");
    assert.containsN($, ".o-mail-ActivityMenu .o-mail-ActivityGroup", 2);
    assert.containsOnce($, ".o-mail-ActivityMenu .o-mail-ActivityGroup:contains('res.partner'):contains('0 Late')");
    assert.containsOnce($, ".o-mail-ActivityMenu .o-mail-ActivityGroup:contains('res.partner'):contains('1 Today')");
    assert.containsOnce($, ".o-mail-ActivityMenu .o-mail-ActivityGroup:contains('res.partner'):contains('0 Future')");
    assert.containsOnce($, ".o-mail-ActivityMenu .o-mail-ActivityGroup:contains('mail.test.activity'):contains('1 Late')");
    assert.containsOnce($, ".o-mail-ActivityMenu .o-mail-ActivityGroup:contains('mail.test.activity'):contains('1 Today')");
    assert.containsOnce($, ".o-mail-ActivityMenu .o-mail-ActivityGroup:contains('mail.test.activity'):contains('2 Future')");
    actionChecks.res_model = 'res.partner';
    await click(".o-mail-ActivityMenu .o-mail-ActivityGroup:contains('res.partner')");
    assert.containsNone($, ".o-mail-ActivityMenu");
    await click(".o_menu_systray i[aria-label='Activities']");
    actionChecks.res_model = 'mail.test.activity';
    await click(".o-mail-ActivityMenu .o-mail-ActivityGroup:contains('mail.test.activity')");
    assert.verifySteps(["do_action:res.partner", "do_action:mail.test.activity"]);
});

QUnit.test("activity menu widget: close on messaging menu click", async (assert) => {
    await start();
    await click(".o_menu_systray i[aria-label='Activities']");
    assert.containsOnce($, ".o-mail-ActivityMenu");
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsNone($, ".o-mail-ActivityMenu");
});
