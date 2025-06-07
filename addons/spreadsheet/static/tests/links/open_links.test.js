import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { makeSpreadsheetMockEnv } from "@spreadsheet/../tests/helpers/model";
import { makeMockEnv, mockService, patchWithCleanup } from "@web/../tests/web_test_helpers";

import { getMenuServerData } from "@spreadsheet/../tests/links/menu_data_utils";

import { setCellContent } from "@spreadsheet/../tests/helpers/commands";
import { getEvaluatedCell } from "@spreadsheet/../tests/helpers/getters";

describe.current.tags("headless");
defineSpreadsheetModels();

const { Model } = spreadsheet;
const { urlRepresentation, openLink } = spreadsheet.links;

test("click a web link", async () => {
    patchWithCleanup(window, {
        open: (href) => {
            expect.step(href.toString());
        },
    });
    const env = await makeMockEnv();
    const data = {
        sheets: [
            {
                cells: { A1: { content: "[Odoo](https://odoo.com)" } },
            },
        ],
    };
    const model = new Model(data, { custom: { env } });
    const cell = getEvaluatedCell(model, "A1");
    expect(urlRepresentation(cell.link, model.getters)).toBe("https://odoo.com");
    openLink(cell.link, env);
    expect.verifySteps(["https://odoo.com"]);
});

test("click a menu link", async () => {
    const fakeActionService = {
        doAction(action) {
            expect.step(action);
        },
        // TODO: this is the conversion 1/1 of the old test, where the mock action service didn't contain a loadAction
        // method, but that's not something that happens in the real world, so we should probably refactor this test
        loadAction: undefined,
    };
    mockService("action", fakeActionService);
    const env = await makeSpreadsheetMockEnv({ serverData: getMenuServerData() });
    const data = {
        sheets: [
            {
                cells: { A1: { content: "[label](odoo://ir_menu_xml_id/test_menu)" } },
            },
        ],
    };
    const model = new Model(data, { custom: { env } });
    const cell = getEvaluatedCell(model, "A1");
    expect(urlRepresentation(cell.link, model.getters)).toBe("menu with xmlid");
    openLink(cell.link, env);
    expect.verifySteps(["spreadsheet.action1"]);
});

test("click a menu link [2]", async () => {
    const fakeActionService = {
        doAction(action) {
            expect.step("do-action");
            expect(action).toEqual({
                name: "an odoo view",
                res_model: "partner",
                target: "current",
                type: "ir.actions.act_window",
                views: [[false, "list"]],
            });
        },
        // TODO: same as the above test
        loadAction: undefined,
    };
    mockService("action", fakeActionService);
    const env = await makeSpreadsheetMockEnv({ serverData: getMenuServerData() });
    const view = {
        name: "an odoo view",
        viewType: "list",
        action: {
            modelName: "partner",
            views: [[false, "list"]],
        },
    };

    const model = new Model({}, { custom: { env } });
    setCellContent(model, "A1", `[a view](odoo://view/${JSON.stringify(view)})`);
    const cell = getEvaluatedCell(model, "A1");
    expect(urlRepresentation(cell.link, model.getters)).toBe("an odoo view");
    openLink(cell.link, env);
    expect.verifySteps(["do-action"]);
});

test("Click a link containing an action xml id", async () => {
    mockService("action", {
        doAction: (action) => {
            expect.step("do-action");
            expect(action.name).toBe("My Action Name");
            expect(action.res_model).toBe("ir.ui.menu");
            expect(action.target).toBe("current");
            expect(action.type).toBe("ir.actions.act_window");
            expect(action.views).toEqual([[false, "list"]]);
            expect(action.domain).toEqual([[1, "=", 1]]);
        },
    });
    const env = await makeSpreadsheetMockEnv({ serverData: getMenuServerData() });

    const view = {
        name: "My Action Name",
        viewType: "list",
        action: {
            modelName: "ir.ui.menu",
            views: [[false, "list"]],
            domain: [[1, "=", 1]],
            xmlId: "spreadsheet.action1",
        },
    };

    const model = new Model({}, { custom: { env } });
    setCellContent(model, "A1", `[an action link](odoo://view/${JSON.stringify(view)})`);
    const cell = getEvaluatedCell(model, "A1");
    expect(urlRepresentation(cell.link, model.getters)).toBe("My Action Name");
    await openLink(cell.link, env);
    await animationFrame();
    expect.verifySteps(["do-action"]);
});

test("Can open link when some views are absent from the referred action", async () => {
    const env = await makeSpreadsheetMockEnv({ serverData: getMenuServerData() });
    env.services.action = {
        ...env.services.action,
        doAction(action) {
            expect.step("do-action");
            expect(action.name).toBe("My Action Name");
            expect(action.res_model).toBe("ir.ui.menu");
            expect(action.target).toBe("current");
            expect(action.type).toBe("ir.actions.act_window");
            expect(action.views).toEqual([
                [false, "list"],
                [false, "form"],
            ]);
            expect(action.domain).toEqual([(1, "=", 1)]);
        },
    };

    const view = {
        name: "My Action Name",
        viewType: "list",
        action: {
            modelName: "ir.ui.menu",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: [(1, "=", 1)],
            xmlId: "spreadsheet.action2",
        },
    };

    const model = new Model({}, { custom: { env } });
    setCellContent(model, "A1", `[an action link](odoo://view/${JSON.stringify(view)})`);
    const cell = getEvaluatedCell(model, "A1");
    expect(urlRepresentation(cell.link, model.getters)).toBe("My Action Name");
    await openLink(cell.link, env);
    await animationFrame();
    expect.verifySteps(["do-action"]);
});

test("Context is passed correctly to the action service", async () => {
    const env = await makeSpreadsheetMockEnv({ serverData: getMenuServerData() });
    env.services.action = {
        ...env.services.action,
        loadAction(_, context) {
            expect.step("load-action");
            expect(context).toEqual({ search_default_partner: 1 });
        },
    };

    const view = {
        name: "My Action Name",
        viewType: "list",
        action: {
            modelName: "ir.ui.menu",
            views: [[false, "list"]],
            domain: [(1, "=", 1)],
            xmlId: "spreadsheet.action1",
            context: { search_default_partner: 1 },
        },
    };

    const model = new Model({}, { custom: { env } });
    setCellContent(model, "A1", `[an action link](odoo://view/${JSON.stringify(view)})`);
    const cell = getEvaluatedCell(model, "A1");
    expect(urlRepresentation(cell.link, model.getters)).toBe("My Action Name");
    await openLink(cell.link, env);
    await animationFrame();
    expect.verifySteps(["load-action"]);
});
