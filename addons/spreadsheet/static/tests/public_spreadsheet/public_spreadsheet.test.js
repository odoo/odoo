import { contains, mockService, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { beforeEach, describe, expect, test } from "@odoo/hoot";

import { mountPublicSpreadsheet } from "@spreadsheet/../tests/helpers/ui";
import { THIS_YEAR_GLOBAL_FILTER } from "@spreadsheet/../tests/helpers/global_filter";
import { addGlobalFilter } from "@spreadsheet/../tests/helpers/commands";
import { freezeOdooData } from "@spreadsheet/helpers/model";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { browser } from "@web/core/browser/browser";
import { setCellContent } from "../helpers/commands";

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
    const { fixture } = await mountPublicSpreadsheet("dashboardDataUrl", "spreadsheet");
    const filterButton = fixture.querySelector(".o-public-spreadsheet-filter-button");
    expect(filterButton).toBe(null);
});

test("show dashboard in dashboard mode when there are global filters", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
    data = await freezeOdooData(model);
    const { fixture } = await mountPublicSpreadsheet("dashboardDataUrl", "dashboard");
    const filterButton = fixture.querySelector(".o-public-spreadsheet-filter-button");
    expect(filterButton).toBeVisible();
});

test("show dashboard in dashboard mode when there are no global filters", async function () {
    const { model } = await createModelWithDataSource();
    data = await freezeOdooData(model);
    const { fixture } = await mountPublicSpreadsheet("dashboardDataUrl", "dashboard");
    const filterButton = fixture.querySelector(".o-public-spreadsheet-filter-button");
    expect(filterButton).toBe(null);
});

test("click filter button can show all filters", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
    data = await freezeOdooData(model);
    const { fixture } = await mountPublicSpreadsheet("dashboardDataUrl", "dashboard");
    await contains(".o-public-spreadsheet-filter-button").click();
    expect(fixture.querySelector(".o-public-spreadsheet-filters")).toBeVisible();
    expect(fixture.querySelector(".o-public-spreadsheet-filter-button")).toBe(null);
});

test("click close button in filter panel will close the panel", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
    data = await freezeOdooData(model);
    const { fixture } = await mountPublicSpreadsheet("dashboardDataUrl", "dashboard");
    await contains(".o-public-spreadsheet-filter-button").click();
    await contains(".o-public-spreadsheet-filters-close-button").click();
    expect(fixture.querySelector(".o-public-spreadsheet-filter-button")).toBeVisible();
    expect(fixture.querySelector(".o-public-spreadsheet-filters")).toBe(null);
});

test("Internal links converted to neutralized are not clickable", async function (assert) {
    const { model } = await createModelWithDataSource();
    setCellContent(model, "A1", "[label](odoo://ir_menu_xml_id/test_menu)");
    data = await freezeOdooData(model);
    const { fixture } = await mountPublicSpreadsheet("dashboardDataUrl", "dashboard");
    expect(fixture.querySelector(".o-dashboard-clickable-cell")).toBe(null);
});

test.tags("desktop");
test("Hides the download button when the downloadExcelUrl is not provided", async function () {
    const { model } = await createModelWithDataSource();
    data = await freezeOdooData(model);
    const { fixture } = await mountPublicSpreadsheet("dashboardDataUrl", "spreadsheet", false);
    await contains(".o-topbar-menu[data-id='file']").click();
    expect(fixture.querySelector(".o-menu-item[data-name='download_public_excel']")).toBe(null);
});

test.tags("desktop");
test("Disable copy button in public spreadsheets", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
    data = await freezeOdooData(model);
    const { fixture } = await mountPublicSpreadsheet("dashboardDataUrl", "spreadsheet");
    await contains(".o-topbar-menu[data-id='edit']").click();
    expect(fixture.querySelector(".o-menu-item[data-name='copy']")).toHaveClass("disabled");
});

describe("sheetId URL synchronization", () => {
    beforeEach(async () => {
        const { model } = await createModelWithDataSource({
            spreadsheetData: {
                sheets: [
                    { id: "sheet1", name: "Sheet1" },
                    { id: "sheet2", name: "Sheet2" },
                ],
            },
        });
        data = await freezeOdooData(model);
    });

    test("activates sheet from URL on initialization", async () => {
        patchWithCleanup(browser.location, {
            href: `${browser.location.href}?sid=sheet2`,
        });
        const { model } = await mountPublicSpreadsheet("dashboardDataUrl", "spreadsheet");
        expect(model.getters.getActiveSheetId()).toBe("sheet2");
    });

    test("falls back to the first sheet and syncs the URL when sid is invalid", async () => {
        patchWithCleanup(browser.location, {
            href: `${browser.location.href}?sid=unknown`,
        });
        const { model } = await mountPublicSpreadsheet("dashboardDataUrl", "spreadsheet");
        expect(new URL(browser.location.href).searchParams.get("sid")).toBe("sheet1");
        expect(model.getters.getActiveSheetId()).toBe("sheet1");
    });

    test("falls back to the first sheet and syncs the URL when sid is absent", async () => {
        const { model } = await mountPublicSpreadsheet("dashboardDataUrl", "spreadsheet");
        expect(model.getters.getActiveSheetId()).toBe("sheet1");
        expect(new URL(browser.location.href).searchParams.get("sid")).toBe("sheet1");
    });

    test("syncs the URL when the active sheet changes", async () => {
        const { model } = await mountPublicSpreadsheet("dashboardDataUrl", "spreadsheet");
        model.dispatch("ACTIVATE_SHEET", {
            sheetIdFrom: "sheet1",
            sheetIdTo: "sheet2",
        });
        expect(new URL(browser.location.href).searchParams.get("sid")).toBe("sheet2");
    });
});
