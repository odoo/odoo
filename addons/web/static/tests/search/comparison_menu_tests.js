/** @odoo-module **/

import { patchDate, patchWithCleanup } from "@web/../tests/helpers/utils";
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
    });

    QUnit.module("Comparison");

    QUnit.test("simple rendering", async function (assert) {
        assert.expect(6);
        patchDate(1997, 0, 9, 12, 0, 0);
        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchMenuTypes: ["filter", "comparison"],
            searchViewId: false,
        });
        assert.containsOnce(controlPanel, ".dropdown.o_filter_menu");
        assert.containsNone(controlPanel, ".dropdown.o_comparison_menu");
        await toggleFilterMenu(controlPanel);
        await toggleMenuItem(controlPanel, "Birthday");
        await toggleMenuItemOption(controlPanel, "Birthday", "January");
        assert.containsOnce(controlPanel, "div.o_comparison_menu > button i.fa.fa-adjust");
        assert.strictEqual(
            controlPanel.el
                .querySelector("div.o_comparison_menu > button span")
                .innerText.trim()
                .toUpperCase() /** @todo why do I need to upperCase */,
            "COMPARISON"
        );
        await toggleComparisonMenu(controlPanel);
        const comparisonOptions = [
            ...controlPanel.el.querySelectorAll(".o_comparison_menu .dropdown-item"),
        ];
        assert.strictEqual(comparisonOptions.length, 2);
        assert.deepEqual(
            comparisonOptions.map((e) => e.innerText.trim()),
            ["Birthday: Previous Period", "Birthday: Previous Year"]
        );
    });

    QUnit.test("activate a comparison works", async function (assert) {
        assert.expect(5);
        patchDate(1997, 0, 9, 12, 0, 0);
        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchMenuTypes: ["filter", "comparison"],
            searchViewId: false,
        });
        await toggleFilterMenu(controlPanel);
        await toggleMenuItem(controlPanel, "Birthday");
        await toggleMenuItemOption(controlPanel, "Birthday", "January");
        await toggleComparisonMenu(controlPanel);
        await toggleMenuItem(controlPanel, "Birthday: Previous Period");
        assert.deepEqual(getFacetTexts(controlPanel), [
            "Birthday: January 1997",
            "Birthday: Previous Period",
        ]);
        await toggleFilterMenu(controlPanel);
        await toggleMenuItem(controlPanel, "Date");
        await toggleMenuItemOption(controlPanel, "Date", "December");
        await toggleComparisonMenu(controlPanel);
        await toggleMenuItem(controlPanel, "Date: Previous Year");
        assert.deepEqual(getFacetTexts(controlPanel), [
            ["Birthday: January 1997", "Date: December 1996"].join("or"),
            "Date: Previous Year",
        ]);
        await toggleFilterMenu(controlPanel);
        await toggleMenuItem(controlPanel, "Date");
        await toggleMenuItemOption(controlPanel, "Date", "1996");
        assert.deepEqual(getFacetTexts(controlPanel), ["Birthday: January 1997"]);
        await toggleComparisonMenu(controlPanel);
        await toggleMenuItem(controlPanel, "Birthday: Previous Year");
        assert.deepEqual(getFacetTexts(controlPanel), [
            "Birthday: January 1997",
            "Birthday: Previous Year",
        ]);
        await removeFacet(controlPanel);
        assert.deepEqual(getFacetTexts(controlPanel), []);
    });
});
