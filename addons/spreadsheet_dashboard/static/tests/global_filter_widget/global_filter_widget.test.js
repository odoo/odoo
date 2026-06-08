import { test, expect, describe, animationFrame } from "@odoo/hoot";
import { contains, mountView, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineSpreadsheetDashboardModels,
    SpreadsheetDashboard,
    SpreadsheetDashboardFavoriteFilters,
} from "../helpers/data";

describe.current.tags("desktop");
defineSpreadsheetDashboardModels();

SpreadsheetDashboardFavoriteFilters._records = [
    {
        id: 1,
        name: "My Default Filters",
        dashboard_id: 1,
        is_default: true,
        user_ids: [],
        global_filters: {},
    },
];

onRpc("ir.model", "has_searchable_parent_relation", ({ args }) =>
    Object.fromEntries((args[0] || []).map((model) => [model, false]))
);

async function mountFavoriteFilterForm() {
    return mountView({
        type: "form",
        resModel: "spreadsheet.dashboard.favorite.filters",
        resId: 1,
        arch: `
            <form>
                <field name="dashboard_id"/>
                <field name="global_filters"
                    widget="global_filters"
                    options="{'dashboard': 'dashboard_id'}"/>
            </form>
        `,
    });
}

test("shows message when dashboard has no global filters", async () => {
    await mountFavoriteFilterForm();
    expect(".o_field_global_filters").toHaveText("No global filters defined for this dashboard.");
});

test("shows message when no dashboard is selected", async () => {
    SpreadsheetDashboardFavoriteFilters._records[0].dashboard_id = false;
    await mountFavoriteFilterForm();
    expect(".o_field_global_filters").toHaveText("Select a dashboard to edit a global filter.");
});

test("global filter widget renders", async () => {
    SpreadsheetDashboard._records[0].spreadsheet_data = JSON.stringify({
        globalFilters: [{ id: "1", type: "date", label: "Period" }],
    });
    await mountFavoriteFilterForm();

    // Widget rendered
    expect(".o_field_global_filters .o-filter-values").toHaveCount(1);
    expect(".o-filter-item > div:first-child").toHaveText("Period");
});

test("editing global filter updates favorite filters record", async () => {
    SpreadsheetDashboard._records[0].spreadsheet_data = JSON.stringify({
        globalFilters: [
            {
                id: "1",
                type: "relation",
                label: "Product",
                modelName: "product",
            },
        ],
    });
    onRpc("spreadsheet.dashboard.favorite.filters", "web_save", ({ args }) => {
        const globalFilter = args[1].global_filters[1];
        expect(globalFilter.ids).toEqual([37]); // xphone
        expect(globalFilter.operator).toBe("not in");
        expect.step("web_save");
    });
    await mountFavoriteFilterForm();
    await contains(".o-filter-values select").select("not in");

    // Pick a product via autocomplete
    await contains(".o-filter-value input").click();
    await contains(".o-autocomplete--dropdown-item:first").click();
    expect(".o_tag .o_tag_badge_text").toHaveText("xphone");

    await contains(".o_form_button_save").click();
    expect.verifySteps(["web_save"]);
});

test("changing dashboard reloads global filters", async () => {
    SpreadsheetDashboard._records[0].spreadsheet_data = JSON.stringify({
        globalFilters: [{ id: "1", type: "date", label: "Period" }],
    });
    SpreadsheetDashboard._records[1].spreadsheet_data = JSON.stringify({
        globalFilters: [
            {
                id: "2",
                type: "relation",
                label: "Product",
                modelName: "product",
            },
        ],
    });
    SpreadsheetDashboardFavoriteFilters._records[0].global_filters = {
        1: { period: "last_90_days", type: "relative" },
    };
    await mountFavoriteFilterForm();
    expect("div[name='dashboard_id'] input").toHaveValue("Dashboard CRM 1");
    expect(".o-filter-value input").toHaveValue("Last 90 Days");
    expect(".o-filter-item > div:first-child").toHaveText("Period");

    // Change dashboard
    await contains("div[name='dashboard_id'] input").click();
    await contains(".o-autocomplete--dropdown-item:nth-child(2)").click();

    await animationFrame();
    expect("div[name='dashboard_id'] input").toHaveValue("Dashboard CRM 2");
    expect(".o-filter-values").toHaveCount(1);
    expect(".o-filter-item > div:first-child").toHaveText("Product");
});

test("clearing a relation global filter resets operator and removes values", async () => {
    SpreadsheetDashboard._records[0].spreadsheet_data = JSON.stringify({
        globalFilters: [
            {
                id: "1",
                type: "relation",
                label: "Product",
                modelName: "product",
            },
        ],
    });
    SpreadsheetDashboardFavoriteFilters._records[0].global_filters = {
        1: { operator: "ilike", strings: ["hello"] },
    };
    await mountFavoriteFilterForm();
    expect(".o-filter-item > div:first-child").toHaveText("Product");
    expect(".o-filter-values select").toHaveValue("ilike");
    expect(".o_tag .o_tag_badge_text").toHaveText("hello");

    // Clear facet
    await contains(".o-filter-clear button").click();
    expect(".o-filter-values select").toHaveValue("in");
    expect(".o_tag .o_tag_badge_text").toHaveCount(0);
});
