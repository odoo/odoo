import { expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { defineModels, getService, onRpc } from "@web/../tests/web_test_helpers";

import { mailModels } from "@mail/../tests/mail_test_helpers";
import { addColumns, deleteColumns, setCellContent } from "@spreadsheet/../tests/helpers/commands";

import { defineQualitySpreadsheetModels } from "./helpers/data";
import { mountQualitySpreadsheetAction } from "./helpers/webclient_helpers";

defineQualitySpreadsheetModels();
defineModels(mailModels);

test("fail with an empty cell", async () => {
    const checkId = 1;
    onRpc("quality.check", "do_fail", ({ args, method }) => {
        expect(args).toEqual([checkId]);
        expect.step(method);
        return true;
    });
    await mountQualitySpreadsheetAction({ check_id: checkId });
    await click("button:contains(Save in The check name)");
    await animationFrame();
    expect.verifySteps(["do_fail"]);
});

test("pass with a truthy cell", async () => {
    const checkId = 1;
    onRpc("quality.check", "do_pass", ({ args, method }) => {
        expect(args).toEqual([checkId]);
        expect.step(method);
        return true;
    });
    const { model } = await mountQualitySpreadsheetAction({ check_id: checkId });
    setCellContent(model, "A1", "1");
    await click("button:contains(Save in The check name)");
    await animationFrame();
    expect.verifySteps(["do_pass"]);
});

test("pass wizard with a truthy cell, do next action", async () => {
    const qualityCheckWizardId = 1;
    const nextCheckSpreadsheetId = 1111;
    onRpc("quality.check.spreadsheet", "join_spreadsheet_session", ({ args }) => {
        if (args[0] === nextCheckSpreadsheetId) {
            expect.step("join next check");
        }
    });
    onRpc("quality.check.wizard", "do_pass", (params) => {
        expect(params.args).toEqual([qualityCheckWizardId]);
        expect.step(params.method);
        // return the next action
        return {
            type: "ir.actions.client",
            tag: "action_spreadsheet_quality",
            params: {
                spreadsheet_id: nextCheckSpreadsheetId,
                ...params,
            },
        };
    });
    const { model } = await mountQualitySpreadsheetAction({
        quality_check_wizard_id: qualityCheckWizardId,
    });
    setCellContent(model, "A1", "1");
    await click("button:contains(Save in The check name)");
    await animationFrame();
    expect.verifySteps(["do_pass", "join next check"]);
});

test("result cell is moved when adding column", async () => {
    const checkId = 1;
    onRpc("quality.check", "do_pass", ({ args, method }) => {
        expect(args).toEqual([checkId]);
        expect.step(method);
        return true;
    });
    onRpc("quality.check.spreadsheet", "write", ({ args }) => {
        expect(args[1].check_cell).toBe("B1");
        expect.step("write");
        return true;
    });
    const { model } = await mountQualitySpreadsheetAction({ check_id: checkId });
    setCellContent(model, "A1", "1");
    addColumns(model, "before", "A", 1);
    await click("button:contains(Save in The check name)");
    await animationFrame();
    expect.verifySteps(["do_pass"]);
    // leave the spreadsheet by going to another
    getService("action").doAction({
        type: "ir.actions.client",
        tag: "action_spreadsheet_quality",
        params: {
            spreadsheet_id: 1111,
        },
    });
    await animationFrame();
    expect.verifySteps(["write"]);
});

test("result cell can be removed", async () => {
    const checkId = 1;
    onRpc("quality.check", "do_pass", ({ method }) => {
        expect.step(method);
        return true;
    });
    onRpc("quality.check.spreadsheet", "write", ({ args }) => {
        expect(args[1].check_cell).toBe("#REF");
        expect.step("write");
        return true;
    });
    const { model } = await mountQualitySpreadsheetAction({ check_id: checkId });
    deleteColumns(model, ["A"]);
    await click("button:contains(Save in The check name)");
    await animationFrame();
    expect.verifySteps(["do_pass"]);
    // leave the spreadsheet by going to another
    getService("action").doAction({
        type: "ir.actions.client",
        tag: "action_spreadsheet_quality",
        params: {
            spreadsheet_id: 1111,
        },
    });
    await animationFrame();
    expect.verifySteps(["write"]);
});

test("invalid check cell is equivalent to no condition", async () => {
    const checkId = 1;
    onRpc("quality.check.spreadsheet", "join_spreadsheet_session", function ({ args }) {
        const data = this.env["quality.check.spreadsheet"].join_spreadsheet_session(...args);
        data.quality_check_cell = "not a valid cell reference";
        return data;
    });
    onRpc("quality.check", "do_pass", ({ method }) => {
        expect.step(method);
        return true;
    });
    await mountQualitySpreadsheetAction({ check_id: checkId });
    await click("button:contains(Save in The check name)");
    await animationFrame();
    expect.verifySteps(["do_pass"]);
});

test("no check cell is equivalent to no condition", async () => {
    const checkId = 1;
    onRpc("quality.check.spreadsheet", "join_spreadsheet_session", function ({ args }) {
        const data = this.env["quality.check.spreadsheet"].join_spreadsheet_session(...args);
        data.quality_check_cell = false; // False = no value in the py orm
        return data;
    });
    onRpc("quality.check", "do_pass", ({ method }) => {
        expect.step(method);
        return true;
    });
    await mountQualitySpreadsheetAction({ check_id: checkId });
    await click("button:contains(Save in The check name)");
    await animationFrame();
    expect.verifySteps(["do_pass"]);
});
