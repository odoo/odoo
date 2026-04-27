import { describe, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

import {
    clickSave,
    fieldInput,
    mockService,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

import { defineHelpdeskModels } from "@helpdesk/../tests/helpdesk_test_helpers";
import { HelpdeskTeam } from "./mock_server/mock_models/helpdesk_team";

describe.current.tags("desktop");
defineHelpdeskModels();

const formViewArch = `
   <form js_class="helpdesk_team_form">
        <sheet>
            <group>
                <field name="name"/>
                <field name="use_sla"/>
                <field name="use_alias"/>
                <field name="use_helpdesk_timesheet"/>
            </group>
        </sheet>
    </form>
`;

onRpc("helpdesk.team", "check_features_enabled", function ({ model, method }) {
    expect.step(method);
    let use_sla = false;
    let use_helpdesk_timesheet = false;
    let use_alias = false;
    for (const record of this.env[model]) {
        if (record.use_sla) {
            use_sla = true;
        }
        if (record.use_helpdesk_timesheet) {
            use_helpdesk_timesheet = true;
        }
        if (record.use_alias) {
            use_alias = true;
        }
    }
    return { use_sla, use_helpdesk_timesheet, use_alias };
});

onRpc("web_save", ({ method }) => expect.step(method));

test("reload the page when use_sla is disabled in all teams", async () => {
    onRpc(({ method, args }) => {
        if (method === "check_modules_to_install") {
            expect.step(method);
            expect(args[0]).toEqual(["use_sla"]);
            return false;
        }
    });
    mockService("action", {
        doAction(action) {
            if (action === "reload_context") {
                expect.step("reload_context");
            }
        },
    });

    await mountView({
        resModel: "helpdesk.team",
        type: "form",
        resIds: [1, 2],
        resId: 1,
        arch: formViewArch,
    });

    await click("div[name='use_sla'] input");
    await clickSave();

    expect.verifySteps([
        "check_features_enabled",
        "web_save",
        "check_features_enabled",
        "reload_context",
    ]);
});

test("reload the page when the feature use_timesheet is enabled in one team", async () => {
    onRpc("check_modules_to_install", ({ method, args }) => {
        expect.step(method);
        expect(args[0]).toEqual(["use_helpdesk_timesheet"]);
        return true;
    });
    mockService("action", {
        doAction(action) {
            if (action === "reload_context") {
                expect.step("reload_context");
            }
        },
    });

    await mountView({
        resModel: "helpdesk.team",
        type: "form",
        resId: 1,
        arch: formViewArch,
    });

    await fieldInput("use_helpdesk_timesheet").check();
    await clickSave();

    expect.verifySteps([
        "check_features_enabled",
        "check_modules_to_install",
        "web_save",
        "reload_context",
    ]);
});

test("do not reload if the feature is already installed", async () => {
    HelpdeskTeam._records[0].use_helpdesk_timesheet = true;
    onRpc("check_modules_to_install", ({ method, args }) => {
        expect.step(method);
        expect(args[0]).toEqual(["use_helpdesk_timesheet"]);
        return false;
    });
    mockService("action", {
        doAction(action) {
            if (action === "reload_context") {
                expect.step("reload_context");
            }
        },
    });

    await mountView({
        resModel: "helpdesk.team",
        type: "form",
        resId: 2,
        arch: formViewArch,
    });

    await fieldInput("use_helpdesk_timesheet").check();
    await clickSave();
    // Check we reload only the first time we enable the timesheet feature in a helpdesk team

    expect.verifySteps(["check_features_enabled", "check_modules_to_install", "web_save"]);
});

test("reload when the feature is disabled in all teams", async () => {
    onRpc("check_modules_to_install", ({ method, args }) => {
        expect.step(method);
        expect(args[0]).toEqual(["use_alias"]);
        return false;
    });
    mockService("action", {
        doAction(action) {
            if (action === "reload_context") {
                expect.step("reload_context");
            }
        },
    });

    await mountView({
        resModel: "helpdesk.team",
        type: "form",
        resIds: [1, 2],
        resId: 1,
        arch: formViewArch,
    });

    await click("div[name='use_alias'] input");
    await clickSave();
    await click(".o_pager_next");
    await animationFrame();
    await click("div[name='use_alias'] input");
    await clickSave();

    expect.verifySteps([
        "check_features_enabled",
        "web_save",
        "check_features_enabled",
        "web_save",
        "check_features_enabled",
        "reload_context",
    ]);
});
