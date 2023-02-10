/** @odoo-module **/

import { start, startServer, click } from "@mail/../tests/helpers/test_utils";

import { session } from "@web/session";
import { date_to_str } from "web.time";
import { patchWithCleanup, getFixture } from "@web/../tests/helpers/utils";

let target;

QUnit.module("test_mail", {
    async beforeEach() {
        target = getFixture();
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
    },
});

QUnit.test("activity menu widget: menu with no records", async function (assert) {
    await start({
        async mockRPC(route, args) {
            if (args.method === "systray_get_activities") {
                return [];
            }
        },
    });
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Activities'])");
    assert.containsOnce(target, ".o-mail-no-activity");
});

QUnit.test("activity menu widget: activity menu with 2 models", async function (assert) {
    const { env } = await start();
    assert.containsOnce(target, ".o_menu_systray i[aria-label='Activities']");
    assert.containsOnce(target, ".o-mail-activity-menu-counter");
    assert.containsOnce(target, ".o-mail-activity-menu-counter:contains(5)");
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
    assert.containsOnce(target, ".o-mail-activity-menu");
    assert.containsN(target, ".o-mail-activity-menu .o-mail-activity-group", 2);
    await click(".o-mail-activity-menu .o-mail-activity-group button:contains('Late')");
    assert.containsNone(target, ".o-mail-activity-menu");
    context = {
        force_search_count: 1,
        search_default_activities_today: 1,
    };
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Activities'])");
    await click(".o-mail-activity-menu .o-mail-activity-group button:contains('Today')");
    context = {
        force_search_count: 1,
        search_default_activities_upcoming_all: 1,
    };
    await click(".o_menu_systray i[aria-label='Activities']");
    await click(".o-mail-activity-menu .o-mail-activity-group button:contains('Future')");
    context = {
        force_search_count: 1,
        search_default_activities_overdue: 1,
        search_default_activities_today: 1,
    };
    await click(".o_menu_systray i[aria-label='Activities']");
    await click(".o-mail-activity-menu .o-mail-activity-group:contains('mail.test.activity')");
});

QUnit.test("activity menu widget: activity view icon", async function (assert) {
    const { env } = await start();
    await click(".o_menu_systray i[aria-label='Activities']");
    assert.containsN(target, "button[title='Summary']", 2);
    const first = $(target).find(
        ".o-mail-activity-group:contains('res.partner') button[title='Summary']"
    );
    const second = $(target).find(
        ".o-mail-activity-group:contains('mail.test.activity') button[title='Summary']"
    );
    assert.ok(first);
    assert.hasClass(first, "fa-clock-o");
    assert.ok(second);
    assert.hasClass(second, "fa-clock-o");
    assert.strictEqual($(target).find(".dropdown-menu").parents(".show").length, 1);
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
    await click(".o-mail-activity-group:contains('mail.test.activity') button[title='Summary']");
    assert.containsNone(target, ".o-dropdown-menu");
    await click(".o_menu_systray i[aria-label='Activities']");
    await click(".o-mail-activity-group:contains('res.partner') button[title='Summary']");
    assert.verifySteps(["do_action:mail.test.activity", "do_action:res.partner"]);
});

QUnit.test("activity menu widget: close on messaging menu click", async function (assert) {
    await start();
    await click(".o_menu_systray i[aria-label='Activities']");
    assert.containsOnce(target, ".o-mail-activity-menu");
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsNone(target, ".o-mail-activity-menu");
});
