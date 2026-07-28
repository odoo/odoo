/** @odoo-module */
import { click } from "@web/../tests/helpers/utils";
import { mountPublicSpreadsheet } from "@spreadsheet/../tests/utils/ui";
import { THIS_YEAR_GLOBAL_FILTER } from "@spreadsheet/../tests/utils/global_filter";
import { addGlobalFilter } from "@spreadsheet/../tests/utils/commands";
import { freezeOdooData } from "../../src/helpers/model";
import { createModelWithDataSource } from "@spreadsheet/../tests/utils/model";

QUnit.module("Public spreadsheet", {}, function () {
    QUnit.test("show spreadsheet in readonly mode", async function (assert) {
        const model = await createModelWithDataSource();
        await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
        const data = await freezeOdooData(model);
        const fixture = await mountPublicSpreadsheet(data, "dashboardDataUrl", "spreadsheet");
        const filterButton = fixture.querySelector(".o-public-spreadsheet-filter-button");
        assert.equal(filterButton, null);
    });

    QUnit.test(
        "show dashboard in dashboard mode when there are global filters",
        async function (assert) {
            const model = await createModelWithDataSource();
            await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
            const data = await freezeOdooData(model);
            const fixture = await mountPublicSpreadsheet(data, "dashboardDataUrl", "dashboard");
            const filterButton = fixture.querySelector(".o-public-spreadsheet-filter-button");
            assert.isVisible(filterButton);
        }
    );

    QUnit.test(
        "show dashboard in dashboard mode when there are no global filters",
        async function (assert) {
            const model = await createModelWithDataSource();
            const data = await freezeOdooData(model);
            const fixture = await mountPublicSpreadsheet(data, "dashboardDataUrl", "dashboard");
            const filterButton = fixture.querySelector(".o-public-spreadsheet-filter-button");
            assert.equal(filterButton, null);
        }
    );

    QUnit.test("click filter button can show all filters", async function (assert) {
        const model = await createModelWithDataSource();
        await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
        const data = await freezeOdooData(model);
        const fixture = await mountPublicSpreadsheet(data, "dashboardDataUrl", "dashboard");
        await click(fixture, ".o-public-spreadsheet-filter-button");
        assert.isVisible(fixture.querySelector(".o-public-spreadsheet-filters"));
        assert.equal(fixture.querySelector(".o-public-spreadsheet-filter-button"), null);
    });

    QUnit.test("click close button in filter panel will close the panel", async function (assert) {
        const model = await createModelWithDataSource();
        await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
        const data = await freezeOdooData(model);
        const fixture = await mountPublicSpreadsheet(data, "dashboardDataUrl", "dashboard");
        await click(fixture, ".o-public-spreadsheet-filter-button");
        await click(fixture, ".o-public-spreadsheet-filters-close-button");
        assert.isVisible(fixture.querySelector(".o-public-spreadsheet-filter-button"));
        assert.equal(fixture.querySelector(".o-public-spreadsheet-filters"), null);
    });
});
