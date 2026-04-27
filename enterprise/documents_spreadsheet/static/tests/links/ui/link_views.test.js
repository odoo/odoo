import {
    defineDocumentSpreadsheetModels,
    getBasicData,
} from "@documents_spreadsheet/../tests/helpers/data";
import { makeDocumentsSpreadsheetMockEnv } from "@documents_spreadsheet/../tests/helpers/model";
import { beforeEach, describe, expect, getFixture, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { Partner } from "@spreadsheet/../tests/helpers/data";
import { makeFakeSpreadsheetService } from "@spreadsheet_edition/../tests/helpers/collaborative_helpers";
import { InsertViewSpreadsheet } from "@spreadsheet_edition/assets/insert_action_link_menu/insert_action_link_menu";
import {
    contains,
    getService,
    mockService,
    mountWithCleanup,
    patchWithCleanup,
    preloadBundle,
    toggleMenu,
    toggleMenuItem,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";
import { loadJS } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { WebClient } from "@web/webclient/webclient";

const { Grid } = spreadsheet.components;

const favoriteMenuRegistry = registry.category("favoriteMenu");

defineDocumentSpreadsheetModels();
preloadBundle("web.fullcalendar_lib");
describe.current.tags("desktop");

let serverData;
async function openView(viewType, options = {}) {
    favoriteMenuRegistry.add(
        "insert-action-link-in-spreadsheet",
        {
            Component: InsertViewSpreadsheet,
            groupNumber: 4,
            isDisplayed: ({ isSmall, config }) =>
                !isSmall && config.actionType === "ir.actions.act_window",
        },
        { sequence: 1 }
    );
    mockService("spreadsheet_collaborative", makeFakeSpreadsheetService());
    await makeDocumentsSpreadsheetMockEnv({
        serverData,
        mockRPC: options.mockRPC,
    });
    const webClient = await mountWithCleanup(WebClient);
    await getService("action").doAction(1, {
        viewType,
        additionalContext: options.additionalContext,
    });
    return webClient;
}

async function insertInSpreadsheetAndClickLink(target) {
    await loadJS("/web/static/lib/Chart/Chart.js");
    patchWithCleanup(Grid.prototype, {
        setup() {
            super.setup();
            this.hoveredCell.hover({ col: 0, row: 0 });
        },
    });
    // Open search bar menu if it is not already
    if (!target.querySelector(".o_search_bar_menu")) {
        await toggleSearchBarMenu();
    }
    await contains(".o_insert_action_spreadsheet_menu").click();
    await contains(".modal-footer button.btn-primary").click();
    await animationFrame();
    await animationFrame();
    await contains(".o-link-tool a").click();
    await animationFrame();
}

function getCurrentViewType(webClient) {
    return webClient.env.services.action.currentController.view.type;
}

function getCurrentAction(webClient) {
    return webClient.env.services.action.currentController.action;
}

let target;

beforeEach(() => {
    target = getFixture();
    serverData = {};
    const models = getBasicData();
    const actions = {
        1: {
            id: 1,
            xml_id: "action_1",
            name: "Partners Action 1",
            res_model: "partner",
            type: "ir.actions.act_window",
            view_mode: "list",
            views: [
                [1, "list"],
                [2, "kanban"],
                [false, "graph"],
                [4, "calendar"],
                [5, "pivot"],
                [6, "map"],
            ],
        },
    };
    const views = {
        "partner,1,list": '<list><field name="foo"/></list>',
        "partner,2,kanban": `<kanban><templates><t t-name="card"><field name="foo"/></t></templates></kanban>`,
        "partner,view_graph_xml_id,graph": /*xml*/ `
                <graph>
                    <field name="probability" type="measure"/>
                </graph>`,
        "partner,4,calendar": `<calendar date_start="date"></calendar>`,
        "partner,5,pivot": /*xml*/ `
                <pivot>
                    <field name="bar" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        "partner,6,map": `<map></map>`,
        "partner,false,search": /*xml*/ `
                <search>
                    <field name="foo"/>
                    <filter name="filter_1" domain="[['name', '=', 'Raoul']]"/>
                    <filter name="filter_2" domain="[['name', '=', False]]"/>
                    <filter name="group_by_name" context="{'group_by':'name'}"/>
                </search>`,
    };
    patchWithCleanup(Partner.prototype, { has_access: () => true });
    serverData = { models, actions, views };
});

test("simple list view", async function () {
    const webClient = await openView("list");
    await insertInSpreadsheetAndClickLink(target);
    expect(getCurrentViewType(webClient)).toBe("list");
});

test("list view with custom domain and groupby", async function () {
    serverData.actions["1"].domain = [["id", "!=", 0]];
    const webClient = await openView("list", {
        additionalContext: { search_default_filter_2: 1 },
    });

    // add a domain
    await toggleSearchBarMenu();
    await toggleMenuItem("filter_1");

    // group by name
    await toggleMenuItem("name");

    await insertInSpreadsheetAndClickLink(target);
    expect(getCurrentViewType(webClient)).toBe("list");
    const action = getCurrentAction(webClient);
    expect(action.domain).toEqual(
        ["&", ["id", "!=", 0], "|", ["name", "=", false], ["name", "=", "Raoul"]],
        { message: "The domain should be the same" }
    );
    expect(action.res_model).toBe("partner");
    expect(action.type).toBe("ir.actions.act_window");
    expect(action.context.group_by).toEqual(["name"], {
        message: "It should be grouped by name",
    });
    expect(".o_group_header").toHaveCount(1, {
        message: "The list view should be grouped",
    });
});

test("insert list in existing spreadsheet", async function () {
    await openView("list", {
        mockRPC: function (route, args) {
            if (args.method === "join_spreadsheet_session") {
                expect.step("spreadsheet-joined");
                expect(args.args[0]).toBe(2, {
                    message: "It should join the selected spreadsheet",
                });
            }
        },
    });
    await loadJS("/web/static/lib/Chart/Chart.js");
    await toggleSearchBarMenu();
    await contains(".o_insert_action_spreadsheet_menu").click();
    await contains(".o-spreadsheet-grid div[data-id='2']").click();
    await contains(".modal-footer button.btn-primary").click();
    await animationFrame();
    expect.verifySteps(["spreadsheet-joined"]);
});

test("insert action in new spreadsheet", async function () {
    await openView("list", {
        mockRPC: async function (route, args) {
            if (args.method === "action_open_new_spreadsheet") {
                expect.step("spreadsheet-created");
            }
        },
    });
    await loadJS("/web/static/lib/Chart/Chart.js");
    expect(".o_spreadsheet_action").toHaveCount(0);
    await toggleSearchBarMenu();
    await contains(".o_insert_action_spreadsheet_menu").click();
    await contains(".modal-footer button.btn-primary").click();
    await animationFrame();
    expect.verifySteps(["spreadsheet-created"]);
    expect(".o_spreadsheet_action").toHaveCount(1);
    expect(".o_navbar .o_sp_name input").toHaveValue("Untitled spreadsheet");
});

test("kanban view", async function () {
    const webClient = await openView("kanban");
    await insertInSpreadsheetAndClickLink(target);
    expect(getCurrentViewType(webClient)).toBe("kanban");
});

test("simple graph view", async function () {
    const webClient = await openView("graph");
    await insertInSpreadsheetAndClickLink(target);
    expect(getCurrentViewType(webClient)).toBe("graph");
});

test("graph view with custom chart type and order", async function () {
    const webClient = await openView("graph");
    await contains(".fa-pie-chart").click();
    // count measure
    await toggleMenu("Measures");
    await toggleMenuItem("Count");
    await insertInSpreadsheetAndClickLink(target);
    const action = getCurrentAction(webClient);
    expect(action.context.graph_mode).toBe("pie", {
        message: "It should be a pie chart",
    });
    expect(action.context.graph_measure).toBe("__count", {
        message: "It should have the custom measures",
    });
    expect(".fa-pie-chart.active").toHaveCount(1);
});

test("calendar view", async function () {
    const webClient = await openView("calendar");
    await insertInSpreadsheetAndClickLink(target);
    expect(getCurrentViewType(webClient)).toBe("calendar");
});

test("simple pivot view", async function () {
    const webClient = await openView("pivot");
    await insertInSpreadsheetAndClickLink(target);
    expect(getCurrentViewType(webClient)).toBe("pivot");
});

test("pivot view with custom group by and measure", async function () {
    const webClient = await openView("pivot");

    // group by name
    await toggleSearchBarMenu();
    await toggleMenuItem("name");

    // add count measure
    await toggleMenu("Measures");
    await toggleMenuItem("Count");

    await insertInSpreadsheetAndClickLink(target);
    const action = getCurrentAction(webClient);

    expect(action.context.pivot_row_groupby).toEqual(["name"], {
        message: "It should be grouped by name",
    });
    expect(action.context.pivot_measures).toEqual(["probability", "__count"], {
        message: "It should have the same two measures",
    });
    expect(".o_pivot_measure_row").toHaveCount(2, {
        message: "It should display the two measures",
    });
});

// TODO: we don't depend of web_enterprise (or base_setup) so map views are not available.
// we should probably move this to test_spreadsheet_edition & add a dependency there
test.skip("map view", async function () {
    const webClient = await openView("map");
    await insertInSpreadsheetAndClickLink(target);
    expect(getCurrentViewType(webClient)).toBe("map");
});

test("action with domain being the empty string", async function () {
    serverData.actions["1"].domain = "";
    const webClient = await openView("list");
    await insertInSpreadsheetAndClickLink(target);
    expect(getCurrentViewType(webClient)).toBe("list");
});
