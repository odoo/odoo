import { contains, mockService } from "@web/../tests/web_test_helpers";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { expect, test } from "@odoo/hoot";

import { mountPublicSpreadsheet } from "@spreadsheet/../tests/helpers/ui";
import { THIS_YEAR_GLOBAL_FILTER } from "@spreadsheet/../tests/helpers/global_filter";
import { addGlobalFilter } from "@spreadsheet/../tests/helpers/commands";
import { freezeOdooData } from "@spreadsheet/helpers/model";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";

defineSpreadsheetModels();

let data;
mockService("http", {
    get: (route, params) => {
        if (route === "dashboardDataUrl") {
            return data;
        }
    },
});

test("show spreadsheet in readonly mode", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
    data = await freezeOdooData(model);
    const fixture = await mountPublicSpreadsheet("dashboardDataUrl", "spreadsheet");
    const filterButton = fixture.querySelector(".o-public-spreadsheet-filter-button");
    expect(filterButton).toBe(null);
});

test("show dashboard in dashboard mode when there are global filters", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
    data = await freezeOdooData(model);
    const fixture = await mountPublicSpreadsheet("dashboardDataUrl", "dashboard");
    const filterButton = fixture.querySelector(".o-public-spreadsheet-filter-button");
    expect(filterButton).toBeVisible();
});

test("show dashboard in dashboard mode when there are no global filters", async function () {
    const { model } = await createModelWithDataSource();
    data = await freezeOdooData(model);
    const fixture = await mountPublicSpreadsheet("dashboardDataUrl", "dashboard");
    const filterButton = fixture.querySelector(".o-public-spreadsheet-filter-button");
    expect(filterButton).toBe(null);
});

test("click filter button can show all filters", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
    data = await freezeOdooData(model);
    const fixture = await mountPublicSpreadsheet("dashboardDataUrl", "dashboard");
    await contains(".o-public-spreadsheet-filter-button").click();
    expect(fixture.querySelector(".o-public-spreadsheet-filters")).toBeVisible();
    expect(fixture.querySelector(".o-public-spreadsheet-filter-button")).toBe(null);
});

test("click close button in filter panel will close the panel", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
    data = await freezeOdooData(model);
    const fixture = await mountPublicSpreadsheet("dashboardDataUrl", "dashboard");
    await contains(".o-public-spreadsheet-filter-button").click();
    await contains(".o-public-spreadsheet-filters-close-button").click();
    expect(fixture.querySelector(".o-public-spreadsheet-filter-button")).toBeVisible();
    expect(fixture.querySelector(".o-public-spreadsheet-filters")).toBe(null);
});

test.tags("desktop");
test("Hides the download button when the downloadExcelUrl is not provided", async function () {
    const { model } = await createModelWithDataSource();
    data = await freezeOdooData(model);
    const fixture = await mountPublicSpreadsheet("dashboardDataUrl", "spreadsheet", false);
    await contains(".o-topbar-menu[data-id='file']").click();
    expect(fixture.querySelector(".o-menu-item[data-name='download_public_excel']")).toBe(null);
});
