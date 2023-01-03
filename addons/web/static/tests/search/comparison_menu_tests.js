/** @odoo-module **/

import { getFixture, patchDate, patchWithCleanup } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import {
    getFacetTexts,
    makeWithSearch,
    removeFacet,
    setupControlPanelServiceRegistry,
    toggleComparisonMenu,
    toggleFilterMenu,
    toggleMenuItem,
    toggleMenuItemOption,
} from "./helpers";

let target;
let serverData;
QUnit.module("Search", (hooks) => {
    hooks.beforeEach(async () => {
        serverData = {
            models: {
                foo: {
                    fields: {
                        birthday: { string: "Birthday", type: "date", store: true, sortable: true },
                        date_field: { string: "Date", type: "date", store: true, sortable: true },
                    },
                },
            },
            views: {
                "foo,false,search": `
          <search>
            <filter name="birthday" date="birthday"/>
            <filter name="date_field" date="date_field"/>
          </search>
        `,
            },
        };
        setupControlPanelServiceRegistry();
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout: () => {},
        });
        target = getFixture();
    });

    QUnit.module("Comparison");

    QUnit.test("simple rendering", async function (assert) {
        patchDate(1997, 0, 9, 12, 0, 0);
        await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchMenuTypes: ["filter", "comparison"],
            searchViewId: false,
        });
        assert.containsOnce(target, ".dropdown.o_filter_menu");
        assert.containsNone(target, ".dropdown.o_comparison_menu");
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "Birthday");
        await toggleMenuItemOption(target, "Birthday", "January");
        assert.containsOnce(target, "div.o_comparison_menu > button i.fa.fa-adjust");
        assert.strictEqual(
            target
                .querySelector("div.o_comparison_menu > button span")
                .innerText.trim()
                .toUpperCase() /** @todo why do I need to upperCase */,
            "COMPARISON"
        );
        await toggleComparisonMenu(target);
        assert.containsN(target, ".o_comparison_menu .dropdown-item", 2);
        assert.containsN(target, ".o_comparison_menu .dropdown-item[role=menuitemcheckbox]", 2);
        const comparisonOptions = [...target.querySelectorAll(".o_comparison_menu .dropdown-item")];
        assert.deepEqual(
            comparisonOptions.map((e) => e.innerText.trim()),
            ["Birthday: Previous Period", "Birthday: Previous Year"]
        );
        assert.deepEqual(
            comparisonOptions.map((e) => e.ariaChecked),
            ["false", "false"]
        );
    });

    QUnit.test("activate a comparison works", async function (assert) {
        patchDate(1997, 0, 9, 12, 0, 0);
        await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchMenuTypes: ["filter", "comparison"],
            searchViewId: false,
        });
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "Birthday");
        await toggleMenuItemOption(target, "Birthday", "January");
        await toggleComparisonMenu(target);
        await toggleMenuItem(target, "Birthday: Previous Period");
        assert.deepEqual(getFacetTexts(target), [
            "Birthday: January 1997",
            "Birthday: Previous Period",
        ]);
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "Date");
        await toggleMenuItemOption(target, "Date", "December");
        await toggleComparisonMenu(target);
        await toggleMenuItem(target, "Date: Previous Year");
        assert.deepEqual(getFacetTexts(target), [
            ["Birthday: January 1997", "Date: December 1996"].join("or"),
            "Date: Previous Year",
        ]);
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "Date");
        await toggleMenuItemOption(target, "Date", "1996");
        assert.deepEqual(getFacetTexts(target), ["Birthday: January 1997"]);
        await toggleComparisonMenu(target);
        await toggleMenuItem(target, "Birthday: Previous Year");
        assert.containsN(target, ".o_comparison_menu .dropdown-item", 2);
        assert.containsN(target, ".o_comparison_menu .dropdown-item[role=menuitemcheckbox]", 2);
        const comparisonOptions = [...target.querySelectorAll(".o_comparison_menu .dropdown-item")];
        assert.deepEqual(
            comparisonOptions.map((e) => e.innerText.trim()),
            ["Birthday: Previous Period", "Birthday: Previous Year"]
        );
        assert.deepEqual(
            comparisonOptions.map((e) => e.ariaChecked),
            ["false", "true"]
        );
        assert.deepEqual(getFacetTexts(target), [
            "Birthday: January 1997",
            "Birthday: Previous Year",
        ]);
        await removeFacet(target);
        assert.deepEqual(getFacetTexts(target), []);
    });
});
