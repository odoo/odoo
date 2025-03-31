import { start, startServer } from "@mail/../tests/mail_test_helpers";
import { assertSteps, click, contains, step } from "@mail/../tests/mail_test_helpers_contains";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { defineTestMailModels } from "@test_mail/../tests/test_mail_test_helpers";
import { serializeDate, today } from "@web/core/l10n/dates";
import { user } from "@web/core/user";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineTestMailModels();
// Avoid problem around midnight (Ex.: tomorrow activities become today activities when reaching midnight)
beforeEach(() => mockDate("2023-4-8 10:00:00", 0));

test("menu with no records", async () => {
    await start();
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Activities'])");
    await contains(".o-mail-ActivityMenu", {
        text: "Congratulations, you're done with your activities.",
    });
});

test("do not show empty text when at least some future activities", async () => {
    const tomorrow = today().plus({ days: 1 });
    const pyEnv = await startServer();
    const activityId = pyEnv["mail.test.activity"].create({});
    pyEnv["mail.activity"].create([
        {
            date_deadline: serializeDate(tomorrow),
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

test("activity menu widget: activity menu with 2 models", async () => {
    const tomorrow = today().plus({ days: 1 });
    const yesterday = today().plus({ days: -1 });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const activityIds = pyEnv["mail.test.activity"].create([{}, {}, {}, {}]);
    pyEnv["mail.activity"].create([
        { res_id: partnerId, res_model: "res.partner", date_deadline: serializeDate(today()) },
        {
            res_id: activityIds[0],
            res_model: "mail.test.activity",
            date_deadline: serializeDate(today()),
        },
        {
            date_deadline: serializeDate(tomorrow),
            res_id: activityIds[1],
            res_model: "mail.test.activity",
        },
        {
            date_deadline: serializeDate(tomorrow),
            res_id: activityIds[2],
            res_model: "mail.test.activity",
        },
        {
            date_deadline: serializeDate(yesterday),
            res_id: activityIds[3],
            res_model: "mail.test.activity",
        },
    ]);
    const env = await start();
    await contains(".o_menu_systray i[aria-label='Activities']");
    await contains(".o-mail-ActivityMenu-counter");
    await contains(".o-mail-ActivityMenu-counter", { text: "5" });
    const actionChecks = {
        context: {
            force_search_count: 1,
            search_default_activities_overdue: 1,
            search_default_activities_today: 1,
        },
        domain: [["activity_user_id", "=", user.userId]],
    };
    patchWithCleanup(env.services.action, {
        doAction(action) {
            Object.entries(actionChecks).forEach(([key, value]) => {
                if (Array.isArray(value) || typeof value === "object") {
                    expect(action[key]).toEqual(value);
                } else {
                    expect(action[key]).toBe(value);
                }
            });
            step("do_action:" + action.name);
        },
    });
    await click(".o_menu_systray i[aria-label='Activities']");
    await contains(".o-mail-ActivityMenu");
    await contains(".o-mail-ActivityMenu .o-mail-ActivityGroup", { count: 2 });
    await contains(".o-mail-ActivityMenu .o-mail-ActivityGroup", {
        contains: [
            ["div[name='activityTitle']", { text: "res.partner" }],
            ["span", { text: "0 Late" }],
            ["span", { text: "1 Today" }],
            ["span", { text: "0 Future" }],
        ],
    });
    await contains(".o-mail-ActivityMenu .o-mail-ActivityGroup", {
        contains: [
            ["div[name='activityTitle']", { text: "mail.test.activity" }],
            ["span", { text: "1 Late" }],
            ["span", { text: "1 Today" }],
            ["span", { text: "2 Future" }],
        ],
    });
    actionChecks.res_model = "res.partner";
    await click(".o-mail-ActivityMenu .o-mail-ActivityGroup", { text: "res.partner" });
    await contains(".o-mail-ActivityMenu", { count: 0 });
    await click(".o_menu_systray i[aria-label='Activities']");
    actionChecks.res_model = "mail.test.activity";
    await click(".o-mail-ActivityMenu .o-mail-ActivityGroup", { text: "mail.test.activity" });
    await assertSteps(["do_action:res.partner", "do_action:mail.test.activity"]);
});

test("activity menu widget: close on messaging menu click", async () => {
    await start();
    await click(".o_menu_systray i[aria-label='Activities']");
    await contains(".o-mail-ActivityMenu");
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-ActivityMenu", { count: 0 });
});
