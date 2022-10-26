/** @odoo-module **/

import {
    click,
    getFixture,
    nextTick,
    patchDate,
    patchTimeZone,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { localization } from "@web/core/l10n/localization";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { browser } from "@web/core/browser/browser";
import {
    addCondition,
    applyFilter,
    editConditionField,
    editConditionOperator,
    editConditionValue,
    getFacetTexts,
    isItemSelected,
    makeWithSearch,
    removeFacet,
    setupControlPanelServiceRegistry,
    toggleAddCustomFilter,
    toggleFilterMenu,
    toggleMenuItem,
} from "./helpers";

function getDomain(controlPanel) {
    return controlPanel.env.searchModel.domain;
}

let target;
let serverData;
QUnit.module("Search", (hooks) => {
    hooks.beforeEach(async () => {
        serverData = {
            models: {
                foo: {
                    fields: {
                        date_field: {
                            name: "date_field",
                            string: "A date",
                            type: "date",
                            searchable: true,
                        },
                        date_time_field: {
                            name: "date_time_field",
                            string: "DateTime",
                            type: "datetime",
                            searchable: true,
                        },
                        boolean_field: {
                            name: "boolean_field",
                            string: "Boolean Field",
                            type: "boolean",
                            default: true,
                            searchable: true,
                        },
                        char_field: {
                            name: "char_field",
                            string: "Char Field",
                            type: "char",
                            default: "foo",
                            trim: true,
                            searchable: true,
                        },
                        float_field: {
                            name: "float_field",
                            string: "Floaty McFloatface",
                            type: "float",
                            digits: [999, 1],
                            searchable: true,
                        },
                        color: {
                            name: "color",
                            string: "Color",
                            type: "selection",
                            selection: [
                                ["black", "Black"],
                                ["white", "White"],
                            ],
                            searchable: true,
                        },
                    },
                    records: {},
                },
            },
            views: {
                "foo,false,search": `<search/>`,
            },
        };
        setupControlPanelServiceRegistry();
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout: () => {},
        });
        target = getFixture();
    });

    QUnit.module("CustomFilterItem");

    QUnit.test("basic rendering", async function (assert) {
        assert.expect(14);

        await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchViewId: false,
            searchMenuTypes: ["filter"],
        });

        await toggleFilterMenu(target);

        const customFilterItem = target.querySelector(".o_add_custom_filter_menu");

        assert.strictEqual(customFilterItem.innerText.trim(), "Add Custom Filter");

        await toggleAddCustomFilter(target);

        // Single condition
        assert.containsOnce(customFilterItem, ".o_filter_condition");
        assert.containsOnce(
            customFilterItem,
            ".o_filter_condition > select.o_generator_menu_field"
        );
        assert.containsOnce(
            customFilterItem,
            ".o_filter_condition > select.o_generator_menu_operator"
        );
        assert.containsOnce(customFilterItem, ".o_filter_condition > span.o_generator_menu_value");
        assert.containsNone(customFilterItem, ".o_filter_condition .o_or_filter");
        assert.containsNone(customFilterItem, ".o_filter_condition .o_generator_menu_delete");

        // no deletion allowed on single condition
        assert.containsNone(customFilterItem, ".o_filter_condition > i.o_generator_menu_delete");

        // Buttons
        assert.containsOnce(customFilterItem, "button.o_apply_filter");
        assert.containsOnce(customFilterItem, "button.o_add_condition");

        assert.containsOnce(customFilterItem, ".o_filter_condition");

        await click(customFilterItem, "button.o_add_condition");

        assert.containsN(customFilterItem, ".o_filter_condition", 2);
        assert.containsOnce(customFilterItem, ".o_filter_condition .o_or_filter");
        assert.containsN(customFilterItem, ".o_filter_condition .o_generator_menu_delete", 2);
    });

    QUnit.test(
        'should have Date and ID field proposed in that order in "Add custom Filter" submenu',
        async function (assert) {
            assert.expect(2);

            await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: ControlPanel,
                searchViewId: false,
                searchMenuTypes: ["filter"],
                searchViewFields: {
                    date_field: {
                        name: "date_field",
                        string: "Date",
                        type: "date",
                        store: true,
                        sortable: true,
                        searchable: true,
                    },
                    foo: { string: "Foo", type: "char", store: true, sortable: true },
                },
            });

            await toggleFilterMenu(target);
            await toggleAddCustomFilter(target);
            const optionEls = target.querySelectorAll(
                ".o_filter_condition > select.o_generator_menu_field option"
            );
            assert.strictEqual(optionEls[0].innerText.trim(), "Date");
            assert.strictEqual(optionEls[1].innerText.trim(), "ID");
        }
    );

    QUnit.test("deactivate a new custom filter works", async function (assert) {
        assert.expect(4);

        patchDate(2020, 1, 5, 12, 20, 0);

        await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchViewId: false,
            searchMenuTypes: ["filter"],
            searchViewFields: {
                date_field: {
                    name: "date_field",
                    string: "Date",
                    type: "date",
                    store: true,
                    sortable: true,
                    searchable: true,
                },
            },
        });

        await toggleFilterMenu(target);
        await toggleAddCustomFilter(target);
        await applyFilter(target);

        assert.ok(isItemSelected(target, 'Date is equal to "02/05/2020"'));
        assert.deepEqual(getFacetTexts(target), ['Date is equal to "02/05/2020"']);

        await toggleMenuItem(target, 'Date is equal to "02/05/2020"');

        assert.notOk(isItemSelected(target, 'Date is equal to "02/05/2020"'));
        assert.deepEqual(getFacetTexts(target), []);
    });

    QUnit.test("custom OR filter presets new condition from preceding", async function (assert) {
        assert.expect(4);

        await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchViewId: false,
            searchMenuTypes: ["filter"],
        });

        await toggleFilterMenu(target);
        await toggleAddCustomFilter(target);

        // Retrieve second selectable values for field and operator dropdowns
        const secondFieldName = target.querySelector(
            ".o_generator_menu_field option:nth-of-type(2)"
        ).value;
        const secondOperator = target.querySelector(
            ".o_generator_menu_operator option:nth-of-type(2)"
        ).value;

        // Check if they really exist…
        assert.ok(!!secondFieldName);
        assert.ok(!!secondOperator);

        // Add first filter condition
        await editConditionField(target, 0, secondFieldName);
        await editConditionOperator(target, 0, secondOperator);

        // Add a second conditon on the filter being created
        await addCondition(target);

        // Check the defaults for field and operator dropdowns
        assert.strictEqual(
            target.querySelector(".o_filter_condition:nth-of-type(2) .o_generator_menu_field")
                .value,
            secondFieldName
        );
        assert.strictEqual(
            target.querySelector(".o_filter_condition:nth-of-type(2) .o_generator_menu_operator")
                .value,
            secondOperator
        );
    });

    QUnit.test("add a custom filter works", async function (assert) {
        assert.expect(2);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchViewId: false,
            searchMenuTypes: ["filter"],
            searchViewFields: {},
        });

        await toggleFilterMenu(target);
        await toggleAddCustomFilter(target);
        // choose ID field in 'Add Custom filter' menu and value 1
        await editConditionField(target, 0, "id");
        await editConditionValue(target, 0, 1);

        await applyFilter(target);

        assert.deepEqual(getFacetTexts(target), ['ID is "1"']);
        assert.deepEqual(getDomain(controlPanel), [["id", "=", 1]]);
    });

    QUnit.test("adding a simple filter works", async function (assert) {
        assert.expect(11);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchViewId: false,
            searchMenuTypes: ["filter"],
            searchViewFields: {
                boolean_field: {
                    name: "boolean_field",
                    string: "Boolean Field",
                    type: "boolean",
                    default: true,
                    searchable: true,
                },
            },
        });

        await toggleFilterMenu(target);

        assert.deepEqual(getFacetTexts(target), []);
        assert.deepEqual(getDomain(controlPanel), []);

        assert.containsNone(target, ".o_menu_item");
        assert.containsOnce(target, ".o_add_custom_filter_menu button.dropdown-toggle");
        // the 'Add Custom Filter' menu should be closed;
        assert.containsNone(target, ".o_add_custom_filter_menu .dropdown-menu");

        await toggleAddCustomFilter(target);
        // the 'Add Custom Filter' menu should be open;
        assert.containsOnce(target, ".o_add_custom_filter_menu .dropdown-menu");

        await applyFilter(target);

        assert.deepEqual(getFacetTexts(target), ["Boolean Field is Yes"]);
        assert.deepEqual(getDomain(controlPanel), [["boolean_field", "=", true]]);

        assert.containsOnce(target, ".o_menu_item");
        assert.containsOnce(target, ".o_add_custom_filter_menu button.dropdown-toggle");
        // the 'Add Custom Filter' menu should still be opened;
        assert.containsOnce(target, ".o_add_custom_filter_menu .dropdown-menu");
    });

    QUnit.test("selection field: default and updated value", async function (assert) {
        assert.expect(10);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchViewId: false,
            searchMenuTypes: ["filter"],
        });

        // Default value
        await toggleFilterMenu(target);

        assert.containsN(target, ".o_menu_item", 0);
        assert.containsN(target, ".dropdown-divider", 0);

        await toggleAddCustomFilter(target);
        await editConditionField(target, 0, "color");
        await applyFilter(target);

        assert.deepEqual(getFacetTexts(target), ['Color is "black"']);
        assert.deepEqual(getDomain(controlPanel), [["color", "=", "black"]]);

        assert.containsN(target, ".o_menu_item", 1);
        assert.containsN(target, ".dropdown-divider", 1);

        // deactivate custom filter
        await removeFacet(target);

        // Updated value
        await toggleFilterMenu(target);
        await toggleAddCustomFilter(target);
        await editConditionField(target, 0, "color");
        await editConditionValue(target, 0, "white");
        await applyFilter(target);

        assert.deepEqual(getFacetTexts(target), ['Color is "white"']);
        assert.deepEqual(getDomain(controlPanel), [["color", "=", "white"]]);

        assert.containsN(target, ".o_menu_item", 2);
        assert.containsN(target, ".dropdown-divider", 2);
    });

    QUnit.test(
        "commit search with an extended proposition with field char does not cause a crash",
        async function (assert) {
            assert.expect(12);

            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: ControlPanel,
                searchViewId: false,
                searchMenuTypes: ["filter"],
                searchViewFields: {
                    many2one_field: {
                        name: "many2one_field",
                        string: "AAA",
                        type: "many2one",
                        searchable: true,
                    },
                },
            });

            const steps = [
                {
                    value: `a`,
                    domain: [["many2one_field", "ilike", `a`]],
                    facetContent: `AAA contains "a"`,
                },
                {
                    value: `"a"`,
                    domain: [["many2one_field", "ilike", `"a"`]],
                    facetContent: `AAA contains ""a""`,
                },
                {
                    value: `'a'`,
                    domain: [["many2one_field", "ilike", `'a'`]],
                    facetContent: `AAA contains "'a'"`,
                },
                {
                    value: `'`,
                    domain: [["many2one_field", "ilike", `'`]],
                    facetContent: `AAA contains "'"`,
                },
                {
                    value: `"`,
                    domain: [["many2one_field", "ilike", `"`]],
                    facetContent: `AAA contains """`,
                },
                {
                    value: `\\`,
                    domain: [["many2one_field", "ilike", `\\`]],
                    facetContent: `AAA contains "\\"`,
                },
            ];

            for (const step of steps) {
                await toggleFilterMenu(target);
                await toggleAddCustomFilter(target);
                await editConditionValue(target, 0, step.value);
                await applyFilter(target);

                assert.deepEqual(getFacetTexts(target), [step.facetContent]);
                assert.deepEqual(getDomain(controlPanel), step.domain);

                await removeFacet(target);
            }
        }
    );

    QUnit.test("custom filter date with equal operator", async function (assert) {
        patchTimeZone(-240);
        patchDate(2017, 1, 22, 12, 30, 0);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchViewId: false,
            searchMenuTypes: ["filter"],
        });

        await toggleFilterMenu(target);
        await toggleAddCustomFilter(target);

        await editConditionField(target, 0, "date_field");
        await editConditionOperator(target, 0, "=");
        await editConditionValue(target, 0, "01/01/2017");
        await applyFilter(target);

        assert.deepEqual(getFacetTexts(target), ['A date is equal to "01/01/2017"']);
        assert.deepEqual(getDomain(controlPanel), [["date_field", "=", "2017-01-01"]]);
    });

    QUnit.test("custom filter datetime with equal operator", async function (assert) {
        assert.expect(5);

        patchTimeZone(-240);
        patchDate(2017, 1, 22, 12, 30, 0);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchViewId: false,
            searchMenuTypes: ["filter"],
        });

        await toggleFilterMenu(target);
        await toggleAddCustomFilter(target);

        await editConditionField(target, 0, "date_time_field");

        assert.strictEqual(
            target.querySelector(".o_generator_menu_field").value,
            "date_time_field"
        );
        assert.strictEqual(target.querySelector(".o_generator_menu_operator").value, "between");
        assert.deepEqual(
            [...target.querySelectorAll(".o_generator_menu_value input")].map((v) => v.value),
            ["02/22/2017 00:00:00", "02/22/2017 23:59:59"]
        );

        await editConditionOperator(target, 0, "=");
        await editConditionValue(target, 0, "02/22/2017 11:00:00"); // in TZ
        await applyFilter(target);

        assert.deepEqual(
            getFacetTexts(target),
            ['DateTime is equal to "02/22/2017 11:00:00"'],
            "description should be in localized format"
        );
        assert.deepEqual(
            getDomain(controlPanel),
            [["date_time_field", "=", "2017-02-22 15:00:00"]],
            "domain should be in UTC format"
        );
    });

    QUnit.test("custom filter datetime between operator", async function (assert) {
        assert.expect(5);

        patchTimeZone(-240);
        patchDate(2017, 1, 22, 12, 30, 0);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchViewId: false,
            searchMenuTypes: ["filter"],
        });

        await toggleFilterMenu(target);
        await toggleAddCustomFilter(target);
        await editConditionField(target, 0, "date_time_field");

        assert.strictEqual(
            target.querySelector(".o_generator_menu_field").value,
            "date_time_field"
        );
        assert.strictEqual(target.querySelector(".o_generator_menu_operator").value, "between");
        assert.deepEqual(
            [...target.querySelectorAll(".o_generator_menu_value input")].map((v) => v.value),
            ["02/22/2017 00:00:00", "02/22/2017 23:59:59"]
        );

        await editConditionValue(target, 0, "02/22/2017 11:00:00", 0); // in TZ
        await editConditionValue(target, 0, "02-22-2017 17:00:00", 1); // in TZ
        await applyFilter(target);

        assert.deepEqual(
            getFacetTexts(target),
            ['DateTime is between "02/22/2017 11:00:00 and 02/22/2017 17:00:00"'],
            "description should be in localized format"
        );
        assert.deepEqual(
            getDomain(controlPanel),
            [
                "&",
                ["date_time_field", ">=", "2017-02-22 15:00:00"],
                ["date_time_field", "<=", "2017-02-22 21:00:00"],
            ],
            "domain should be in UTC format"
        );
    });

    QUnit.test("input value parsing", async function (assert) {
        assert.expect(7);

        await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchViewId: false,
            searchMenuTypes: ["filter"],
        });

        await toggleFilterMenu(target);
        await toggleAddCustomFilter(target);
        await addCondition(target);

        await editConditionField(target, 0, "float_field");
        await editConditionField(target, 1, "id");

        const [floatInput, idInput] = target.querySelectorAll(".o_generator_menu_value .o_input");

        // Default values
        await editConditionValue(target, 0, "0.0");
        assert.strictEqual(floatInput.value, "0.0");

        await editConditionValue(target, 1, "0");
        assert.strictEqual(idInput.value, "0");

        // Float parsing
        await editConditionValue(target, 0, "4.2");
        assert.strictEqual(floatInput.value, "4.2");

        await editConditionValue(target, 0, "DefinitelyValidFloat");
        // "DefinitelyValidFloat" cannot be entered in a input type number so that the input value is reset to 0
        assert.strictEqual(floatInput.value, "4.2");

        // Number parsing
        await editConditionValue(target, 1, "4");
        assert.strictEqual(idInput.value, "4");

        await editConditionValue(target, 1, "4.2");
        assert.strictEqual(idInput.value, "4");

        await editConditionValue(target, 1, "DefinitelyValidID");
        // "DefinitelyValidID" cannot be entered in a input type number so that the input value is reset to 0
        assert.strictEqual(idInput.value, "0");
    });

    QUnit.test("input value parsing with language", async function (assert) {
        assert.expect(5);

        await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchViewId: false,
            searchMenuTypes: ["filter"],
        });

        // Needs to be done after services have been started
        patchWithCleanup(localization, {
            decimalPoint: ",",
            thousandsSep: "",
            grouping: [3, 0],
        });

        await toggleFilterMenu(target);
        await toggleAddCustomFilter(target);

        await editConditionField(target, 0, "float_field");

        const [floatInput] = target.querySelectorAll(".o_generator_menu_value .o_input");

        // Default values
        assert.strictEqual(floatInput.value, "0,0");

        // Float parsing
        await editConditionValue(target, 0, "4,");
        assert.strictEqual(floatInput.value, "4,0");

        await editConditionValue(target, 0, "4,2");
        assert.strictEqual(floatInput.value, "4,2");

        await editConditionValue(target, 0, "4,2,");
        assert.strictEqual(floatInput.value, "42,0"); // because of the en localization fallback in parsers.

        await editConditionValue(target, 0, "DefinitelyValidFloat");

        // The input here is a string, resulting in a parsing error instead of 0
        assert.strictEqual(floatInput.value, "42,0");
    });

    QUnit.test("add custom filter with multiple values", async function (assert) {
        assert.expect(2);

        const controlPanel = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchViewId: false,
            searchMenuTypes: ["filter"],
        });

        await toggleFilterMenu(target);
        await toggleAddCustomFilter(target);

        for (let i = 0; i < 4; i++) {
            await addCondition(target);
        }

        await editConditionField(target, 0, "date_field");
        await editConditionValue(target, 0, "01/09/1997");

        await editConditionField(target, 1, "boolean_field");
        await editConditionOperator(target, 1, "!=");

        await editConditionField(target, 2, "char_field");
        await editConditionValue(target, 2, "I will be deleted anyway");

        await editConditionField(target, 3, "float_field");
        await editConditionValue(target, 3, 7.2);

        await editConditionField(target, 4, "id");
        await editConditionValue(target, 4, 9);

        const thirdcondition = target.querySelectorAll(".o_filter_condition")[2];

        await click(thirdcondition, ".o_generator_menu_delete");
        await applyFilter(target);

        assert.deepEqual(getFacetTexts(target), [
            [
                'A date is equal to "01/09/1997"',
                "Boolean Field is No",
                'Floaty McFloatface is equal to "7.2"',
                'ID is "9"',
            ].join("or"),
        ]);
        assert.deepEqual(getDomain(controlPanel), [
            "|",
            ["date_field", "=", "1997-01-09"],
            "|",
            ["boolean_field", "!=", true],
            "|",
            ["float_field", "=", 7.2],
            ["id", "=", 9],
        ]);
    });

    QUnit.test("delete button is visible", async function (assert) {
        await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchViewId: false,
            searchMenuTypes: ["filter"],
        });

        await toggleFilterMenu(target);
        await toggleAddCustomFilter(target);

        assert.containsNone(
            target,
            ".o_generator_menu_delete",
            "There is no delete button by default"
        );

        await addCondition(target);
        assert.containsN(
            target,
            ".o_generator_menu_delete",
            2,
            "A delete button has been added to each condition"
        );
        assert.containsN(
            target,
            "i.o_generator_menu_delete.fa-trash-o",
            2,
            "The delete button is shown as a trash icon"
        );
    });

    QUnit.test("condition value is not lost on deep render", async function (assert) {
        const component = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchViewId: false,
            searchMenuTypes: ["filter"],
        });

        await toggleFilterMenu(target);
        await toggleAddCustomFilter(target);

        await editConditionField(target, 0, "char_field");
        await editConditionValue(target, 0, "Coucou", 0, false);

        let charInput = target.querySelector(".o_generator_menu_value .o_input");
        assert.strictEqual(charInput.value, "Coucou");

        component.render(true);
        await nextTick();

        charInput = target.querySelector(".o_generator_menu_value .o_input");
        assert.strictEqual(charInput.value, "Coucou");
    });
});
