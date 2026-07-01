import {
    contains,
    getMockEnv,
    mockService,
    mountWithCleanup,
} from "@web/../tests/web_test_helpers";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { animationFrame, expect, getFixture, test } from "@odoo/hoot";

import { THIS_YEAR_GLOBAL_FILTER } from "@spreadsheet/../tests/helpers/global_filter";
import { addGlobalFilter } from "@spreadsheet/../tests/helpers/commands";
import { freezeOdooData } from "@spreadsheet/helpers/model";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { PublicDashboard } from "../../src/public/public_dashboard";

defineSpreadsheetModels();

/**
 * Mount public dashboard component with the given data
 * @returns {Promise<HTMLElement>}
 */
async function mountPublicDashboard(dataUrl) {
    const env = getMockEnv();
    env.isFrozenSpreadsheet = () => true;
    const component = await mountWithCleanup(PublicDashboard, {
        props: {
            dataUrl,
        },
    });
    await animationFrame();
    return {
        fixture: getFixture(),
        model: component.model,
    };
}

let data;
mockService("http", {
    get: (route, params) => {
        if (route === "dashboardDataUrl") {
            return data;
        }
    },
});

test("show dashboard in dashboard mode when there are global filters", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
    data = await freezeOdooData(model);
    const { fixture } = await mountPublicDashboard("dashboardDataUrl");
    const filterButton = fixture.querySelector(".o-public-spreadsheet-filter-button");
    expect(filterButton).toBeVisible();
});

test("show dashboard in dashboard mode when there are no global filters", async function () {
    const { model } = await createModelWithDataSource();
    data = await freezeOdooData(model);
    const { fixture } = await mountPublicDashboard("dashboardDataUrl");
    const filterButton = fixture.querySelector(".o-public-spreadsheet-filter-button");
    expect(filterButton).toBe(null);
});

test("click filter button can show all filters", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
    data = await freezeOdooData(model);
    const { fixture } = await mountPublicDashboard("dashboardDataUrl");
    await contains(".o-public-spreadsheet-filter-button").click();
    expect(fixture.querySelector(".o-public-spreadsheet-filters")).toBeVisible();
    expect(fixture.querySelector(".o-public-spreadsheet-filter-button")).toBe(null);
});

test("click close button in filter panel will close the panel", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
    data = await freezeOdooData(model);
    const { fixture } = await mountPublicDashboard("dashboardDataUrl");
    await contains(".o-public-spreadsheet-filter-button").click();
    await contains(".o-public-spreadsheet-filters-close-button").click();
    expect(fixture.querySelector(".o-public-spreadsheet-filter-button")).toBeVisible();
    expect(fixture.querySelector(".o-public-spreadsheet-filters")).toBe(null);
});
