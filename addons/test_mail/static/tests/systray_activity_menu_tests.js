/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { serializeDate, today } from "@web/core/l10n/dates";
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

QUnit.test("activity menu widget: activity menu with 2 models", async (assert) => {
    function containsN(domElement, selector, containings) {
        return Array.from(domElement.querySelectorAll(selector)).filter((sel) =>
            containings.every((containing) => sel.textContent.includes(containing))
        ).length;
    }

    const tomorrow = today().plus({ days: 1 });
    const yesterday = today().plus({ days: -1 });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const activityIds = pyEnv["mail.test.activity"].create([{}, {}, {}, {}]);
    pyEnv["mail.activity"].create([
        { res_id: partnerId, res_model: "res.partner" },
        { res_id: activityIds[0], res_model: "mail.test.activity" },
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
    const { env } = await start();
    await contains(".o_menu_systray i[aria-label='Activities']");
    await contains(".o-mail-ActivityMenu-counter");
    await contains(".o-mail-ActivityMenu-counter", { text: "5" });
    const actionChecks = {
        context: { force_search_count: 1 },
        domain: [["activity_user_id", "=", session.uid]],
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
    assert.ok(
        containsN(document, ".o-mail-ActivityMenu .o-mail-ActivityGroup", ["res.partner", "0 Late"])
    );
    assert.ok(
        containsN(document, ".o-mail-ActivityMenu .o-mail-ActivityGroup", ["res.partner", "1 Today"])
    );
    assert.ok(
        containsN(document, ".o-mail-ActivityMenu .o-mail-ActivityGroup", ["res.partner", "0 Future"])
    );
    assert.ok(
        containsN(document, ".o-mail-ActivityMenu .o-mail-ActivityGroup", ["mail.test.activity", "1 Late"])
    );
    assert.ok(
        containsN(document, ".o-mail-ActivityMenu .o-mail-ActivityGroup", ["mail.test.activity", "1 Today"])
    );
    assert.ok(
        containsN(document, ".o-mail-ActivityMenu .o-mail-ActivityGroup", ["mail.test.activity", "2 Future"])
    );
    actionChecks.res_model = "res.partner";
    await click(".o-mail-ActivityMenu .o-mail-ActivityGroup", { text: "res.partner" });
    await contains(".o-mail-ActivityMenu", { count: 0 });
    await click(".o_menu_systray i[aria-label='Activities']");
    actionChecks.res_model = "mail.test.activity";
    await click(".o-mail-ActivityMenu .o-mail-ActivityGroup", { text: "mail.test.activity" });
    assert.verifySteps(["do_action:res.partner", "do_action:mail.test.activity"]);
});

QUnit.test("activity menu widget: close on messaging menu click", async () => {
    await start();
    await click(".o_menu_systray i[aria-label='Activities']");
    await contains(".o-mail-ActivityMenu");
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-ActivityMenu", { count: 0 });
});
