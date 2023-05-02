/** @odoo-module **/

import { Component, xml } from "@odoo/owl";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { MainComponentsContainer } from "@web/core/main_components_container";
import {
    click,
    editInput,
    getFixture,
    getNodesTextContent,
    patchDate,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";
import { fieldService } from "@web/core/field_service";
import { registry } from "@web/core/registry";
import {
    editFavoriteName,
    getFacetTexts,
    makeWithSearch,
    openAdvancedSearchDialog,
    saveFavorite,
    setupControlPanelFavoriteMenuRegistry,
    setupControlPanelServiceRegistry,
    toggleSearchBarMenu,
    toggleMenuItem,
    toggleMenuItemOption,
    toggleSaveFavorite,
} from "./helpers";

async function makeTestComponent(props) {
    class TestComponent extends Component {
        setup() {
            this.id = 1; // used for t-key. We want to be sure that the control panel is rendered.
        }
    }
    TestComponent.components = { MainComponentsContainer, SearchBar };
    TestComponent.template = xml`
        <div class="o_test_component">
            <MainComponentsContainer/>
            <SearchBar t-key="id++"/>
        </div>
    `;
    return makeWithSearch({
        serverData,
        resModel: "foo",
        Component: TestComponent,
        searchViewId: 1,
        searchMenuTypes: ["filter", "groupBy", "comparison", "favorite"],
        ...props,
    });
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
                        binary_field: {
                            name: "binary_field",
                            string: "Binary Field",
                            type: "binary",
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
                        user_id: {
                            string: "User",
                            type: "many2one",
                            relation: "user",
                            store: true,
                            sortable: true,
                        },
                    },
                },
                user: {
                    fields: {
                        id: { string: "Id", type: "integer" },
                        name: { string: "Product Name", type: "char" },
                    },
                    records: [
                        {
                            id: 37,
                            display_name: "Me",
                        },
                    ],
                },
            },
            views: {
                "foo,1,search": `
                    <search>
                        <field name="char_field"/>
                        <filter name="simple_filter" string="Simple Filter" domain="[('float_field', '=', 2)]"/>
                        <filter name="dynamic_filter" string="Dynamic Filter" domain="[('user_id', '=', uid)]"/>
                        <filter name="date_filter" string="Date Filter" date="date_field"/>
                        <filter name="simple_group_by" string="Simple GroupBy" context="{'group_by': 'boolean_field'}"/>
                        <filter name="date_group_by" string="Date GroupBy" context="{'group_by': 'date_time_field'}"/>
                    </search>
                `,
            },
        };
        setupControlPanelServiceRegistry();
        setupControlPanelFavoriteMenuRegistry();
        registry.category("services").add("field", fieldService);
        target = getFixture();
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout: () => {},
        });
    });

    QUnit.module("AdvancedSearchDialog");

    QUnit.test("basic rendering", async function (assert) {
        await makeTestComponent();
        await toggleSearchBarMenu(target);
        assert.containsNone(target, ".modal");
        assert.containsOnce(target, ".o_searchview_dropdown_toggler");

        await openAdvancedSearchDialog(target);
        assert.containsNone(target, ".o_filter_menu .dropdown-menu");
        assert.containsOnce(target, ".modal");
        assert.containsOnce(target, ".modal .modal-header h4");
        assert.strictEqual(target.querySelector(".modal header h4").innerText, "Advanced Search");
        assert.containsN(target, ".modal footer button", 2);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".modal footer button")), [
            "Search",
            "Discard",
        ]);

        await click(target, ".modal footer button:nth-child(2)");
        assert.containsNone(target, ".modal");

        await toggleSearchBarMenu(target);
        await openAdvancedSearchDialog(target);
        assert.containsOnce(target, ".modal");

        await click(target, ".modal footer button:nth-child(1)");
        assert.containsNone(target, ".modal");
    });

    QUnit.test("start with an empty query", async function (assert) {
        await makeTestComponent();
        await toggleSearchBarMenu(target);
        await openAdvancedSearchDialog(target);
        assert.containsOnce(target, ".modal");
        assert.containsOnce(target, ".modal .modal-body .o_domain_selector");
        assert.containsOnce(target, ".modal .modal-body .o_domain_selector span");
        assert.strictEqual(
            target.querySelector(".modal .modal-body .o_domain_selector span").innerText,
            "Match all records"
        );
        assert.containsOnce(
            target,
            ".modal .modal-body .o_domain_selector button.o_domain_add_first_node_button"
        );
    });

    QUnit.test("start with an empty query and a global domain", async function (assert) {
        await makeTestComponent({ domain: [[0, "=", 1]] });
        await toggleSearchBarMenu(target);
        await openAdvancedSearchDialog(target);
        // the global domain should not be part of the domain passed to domain selector
        assert.containsOnce(target, ".modal");
        assert.containsOnce(target, ".modal .modal-body .o_domain_selector");
        assert.containsOnce(target, ".modal .modal-body .o_domain_selector span");
        assert.strictEqual(
            target.querySelector(".modal .modal-body .o_domain_selector span").innerText,
            "Match all records"
        );
        assert.containsOnce(
            target,
            ".modal .modal-body .o_domain_selector button.o_domain_add_first_node_button"
        );
    });

    QUnit.test("start with a simple domain and modify it", async function (assert) {
        const testComponent = await makeTestComponent({
            context: { search_default_simple_filter: true },
        });
        await toggleSearchBarMenu(target);
        assert.deepEqual(getFacetTexts(target), ["Simple Filter"]);
        assert.containsNone(target, ".o_domain_selector");

        await openAdvancedSearchDialog(target);
        assert.containsOnce(target, ".modal");
        assert.containsOnce(target, ".modal .modal-body .o_domain_selector");
        assert.containsOnce(target, ".o_model_field_selector");
        assert.strictEqual(
            target.querySelector(".o_model_field_selector").innerText,
            "Floaty McFloatface"
        );
        assert.containsOnce(target, ".o_domain_leaf_operator_select");
        assert.strictEqual(target.querySelector(".o_domain_leaf_operator_select").value, "equal");
        assert.containsOnce(target, ".o_domain_leaf_value_input");
        assert.strictEqual(target.querySelector(".o_domain_leaf_value_input").value, "2");

        await editInput(target, ".o_domain_leaf_value_input", 4);
        assert.strictEqual(target.querySelector(".o_domain_leaf_value_input").value, "4");
        assert.deepEqual(testComponent.props.domain, [["float_field", "=", 2]]);

        await click(target, ".modal footer button:nth-child(1)");
        assert.deepEqual(getFacetTexts(target), ["Advanced Search"]);
        assert.deepEqual(testComponent.props.domain, [["float_field", "=", 4]]);
    });

    QUnit.test("start with a dynamic domain (evaluation is done)", async function (assert) {
        const testComponent = await makeTestComponent({
            context: {
                search_default_dynamic_filter: true,
            },
            mockRPC(_, { args, method }) {
                if (method === "create_or_replace") {
                    assert.strictEqual(args[0].domain, `[("user_id", "=", 4)]`); // the domain is not saved dynamically
                    return 9; // fake serverId to simulate the creation of
                    // the favorite in db.
                }
            },
        });
        assert.deepEqual(getFacetTexts(target), ["Dynamic Filter"]);
        assert.deepEqual(testComponent.props.domain, [["user_id", "=", 7]]);

        await toggleSearchBarMenu(target);
        await openAdvancedSearchDialog(target);

        assert.strictEqual(target.querySelector(".o_model_field_selector").innerText, "User");
        assert.strictEqual(target.querySelector(".o_domain_leaf_operator_select").value, "equal");
        assert.strictEqual(target.querySelector(".o_ds_value_cell input").value, "7");
    });

    QUnit.test(
        "start with a simple domain and a simple group by, group by not lost after search",
        async function (assert) {
            const testComponent = await makeTestComponent({
                context: {
                    search_default_simple_filter: true,
                    search_default_simple_group_by: true,
                },
            });
            assert.deepEqual(getFacetTexts(target), ["Simple Filter", "Simple GroupBy"]);

            await toggleSearchBarMenu(target);
            await openAdvancedSearchDialog(target);
            assert.strictEqual(target.querySelector(".o_domain_leaf_value_input").value, "2");
            assert.deepEqual(testComponent.props.domain, [["float_field", "=", 2]]);
            assert.deepEqual(testComponent.props.groupBy, ["boolean_field"]);

            await editInput(target, ".o_domain_leaf_value_input", 4);
            await click(target, ".modal footer button:nth-child(1)");
            assert.deepEqual(getFacetTexts(target), ["Simple GroupBy", "Advanced Search"]);
            assert.deepEqual(testComponent.props.domain, [["float_field", "=", 4]]);
            assert.deepEqual(testComponent.props.groupBy, ["boolean_field"]);
        }
    );

    QUnit.test("start with a favorite only", async function (assert) {
        const irFilters = [
            {
                context: "{ 'some_key': 'some_value', 'group_by': ['color'] }",
                domain: "[('char_field', 'ilike', 'abc')]",
                id: 1,
                is_default: true,
                name: "My favorite",
                sort: "[]",
                user_id: [2, "Mitchell Admin"],
            },
        ];
        const testComponent = await makeTestComponent({
            irFilters,
        });
        assert.deepEqual(getFacetTexts(target), ["My favorite"]);
        assert.deepEqual(testComponent.props.domain, [["char_field", "ilike", "abc"]]);
        assert.deepEqual(testComponent.props.groupBy, ["color"]);
        assert.strictEqual(testComponent.props.context.some_key, "some_value");

        await toggleSearchBarMenu(target);
        await openAdvancedSearchDialog(target);
        await editInput(target.querySelector(".o_domain_leaf_value_input"), null, "xyz");
        assert.strictEqual(target.querySelector(".o_domain_leaf_value_input").value, "xyz");

        await click(target, ".modal footer button:nth-child(1)");
        assert.deepEqual(getFacetTexts(target), ["Color", "Advanced Search"]);
        assert.deepEqual(testComponent.props.domain, [["char_field", "ilike", "xyz"]]);
        assert.deepEqual(testComponent.props.groupBy, ["color"]);
        assert.strictEqual(testComponent.props.context.some_key, "some_value");
    });

    QUnit.test("group_bys retrieved from favorite", async function (assert) {
        const irFilters = [
            {
                context: "{ 'some_key': 'some_value', 'group_by': ['color'] }",
                domain: "[('char_field', 'ilike', 'abc')]",
                id: 1,
                is_default: true,
                name: "My favorite",
                sort: "[]",
                user_id: [2, "Mitchell Admin"],
            },
        ];
        const testComponent = await makeTestComponent({
            irFilters,
        });

        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "Simple GroupBy");
        assert.deepEqual(getFacetTexts(target), ["My favorite", "Simple GroupBy"]);

        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "Simple Filter");
        assert.deepEqual(getFacetTexts(target), ["My favorite", "Simple GroupBy", "Simple Filter"]);
        assert.deepEqual(testComponent.props.domain, [
            "&",
            ["char_field", "ilike", "abc"],
            ["float_field", "=", 2],
        ]);
        assert.deepEqual(testComponent.props.groupBy, ["color", "boolean_field"]);
        assert.strictEqual(testComponent.props.context.some_key, "some_value");

        await toggleSearchBarMenu(target);
        await openAdvancedSearchDialog(target);
        await editInput(target.querySelector(".o_domain_leaf_value_input"), null, "xyz");
        assert.strictEqual(target.querySelector(".o_domain_leaf_value_input").value, "xyz");

        await click(target, ".modal footer button:nth-child(1)");
        assert.deepEqual(getFacetTexts(target), ["Color\n>\nSimple GroupBy", "Advanced Search"]);
        assert.deepEqual(testComponent.props.domain, [
            "&",
            ["char_field", "ilike", "xyz"],
            ["float_field", "=", 2],
        ]);
        assert.deepEqual(testComponent.props.groupBy, ["color", "boolean_field"]);
        assert.strictEqual(testComponent.props.context.some_key, "some_value");
    });

    QUnit.test(
        "comparison retrieved from favorite (comparison in searchMenuTypes)",
        async function (assert) {
            patchDate(2023, 2, 1, 14, 0, 0);
            const testComponent = await makeTestComponent({
                async mockRPC(_, { method }) {
                    if (method === "create_or_replace") {
                        return 9;
                    }
                },
            });
            await toggleSearchBarMenu(target);
            await toggleMenuItem(target, "Date Filter");
            await toggleMenuItemOption(target, "Date Filter", "March");

            await toggleSearchBarMenu(target);
            await toggleMenuItem(target, "Date Filter: Previous Period");

            await toggleSearchBarMenu(target);
            await toggleSaveFavorite(target);
            await editFavoriteName(target, "My new favorite");
            await saveFavorite(target, "My new favorite");

            assert.deepEqual(getFacetTexts(target), ["My new favorite"]);
            assert.deepEqual(testComponent.props.domain, []);
            assert.deepEqual(testComponent.props.comparison, {
                domains: [
                    {
                        arrayRepr: [
                            "&",
                            ["date_field", ">=", "2023-03-01"],
                            ["date_field", "<=", "2023-03-31"],
                        ],
                        description: "March 2023",
                    },
                    {
                        arrayRepr: [
                            "&",
                            ["date_field", ">=", "2023-02-01"],
                            ["date_field", "<=", "2023-02-28"],
                        ],
                        description: "February 2023",
                    },
                ],
                fieldName: "date_field",
            });
            assert.deepEqual(testComponent.props.groupBy, []);
            assert.strictEqual(testComponent.props.context.comparison, undefined);

            await toggleSearchBarMenu(target);
            await openAdvancedSearchDialog(target);
            await click(target, ".modal footer button:nth-child(1)");

            assert.deepEqual(getFacetTexts(target), ["Advanced Search"]);
            assert.deepEqual(testComponent.props.domain, [
                "&",
                ["date_field", ">=", "2023-03-01"],
                ["date_field", "<=", "2023-03-31"],
            ]);
            assert.deepEqual(testComponent.props.groupBy, []);
            assert.strictEqual(testComponent.props.context.comparison, undefined);
        }
    );

    QUnit.test(
        "comparison retrieved from favorite (comparison not in searchMenuTypes)",
        async function (assert) {
            const testComponent = await makeTestComponent({
                irFilters: [
                    {
                        context: `{
                            'group_by': [],
                            'comparison': {
                                'comparisonId': 'previous_period',
                                'fieldName': 'create_date',
                                'fieldDescription':'Creation Date',
                                'range': ['&', ['create_date', '>=', '2023-02-28 23:00:00'], ['create_date', '<=', '2023-03-31 21:59:59']],
                                'rangeDescription': 'March 2023',
                                'comparisonRange': ['&', ['create_date', '>=', '2023-01-31 23:00:00'], ['create_date', '<=', '2023-02-28 22:59:59']],
                                'comparisonRangeDescription': 'February 2023'}
                        }`,
                        domain: "[]",
                        id: 1,
                        is_default: true,
                        name: "My favorite",
                        sort: "[]",
                        user_id: [2, "Mitchell Admin"],
                    },
                ],
                searchMenuTypes: ["filter", "favorite"],
            });

            assert.deepEqual(getFacetTexts(target), ["My favorite"]);
            assert.deepEqual(testComponent.props.domain, []); // a problem with comparison?
            assert.strictEqual(testComponent.props.comparison, null);
            assert.deepEqual(testComponent.props.groupBy, []);
            assert.strictEqual(testComponent.props.context.comparison, undefined);

            await toggleSearchBarMenu(target);
            await openAdvancedSearchDialog(target);
            await click(target, ".modal footer button:nth-child(1)");

            assert.deepEqual(getFacetTexts(target), ["Advanced Search"]);
            assert.deepEqual(testComponent.props.domain, []);
            assert.deepEqual(testComponent.props.groupBy, []);
            assert.strictEqual(testComponent.props.context.comparison, undefined);
        }
    );

    QUnit.test("search items created for advanced search are invisible", async function (assert) {
        const irFilters = [
            {
                context: "{ 'group_by': ['color'] }",
                domain: "[]]",
                id: 1,
                is_default: true,
                name: "My favorite",
                sort: "[]",
                user_id: [2, "Mitchell Admin"],
            },
        ];
        const testComponent = await makeTestComponent({
            irFilters,
        });
        assert.deepEqual(getFacetTexts(target), ["My favorite"]);
        assert.deepEqual(testComponent.props.domain, []);
        assert.deepEqual(testComponent.props.groupBy, ["color"]);

        await toggleSearchBarMenu(target);
        const visibleGroupBys = getNodesTextContent(
            target.querySelectorAll(".o_group_by_menu .dropdown-item")
        );
        const visibleFilters = getNodesTextContent(
            target.querySelectorAll(".o_filter_menu .dropdown-item")
        );
        await openAdvancedSearchDialog(target);
        await click(target, ".modal footer button:nth-child(1)");
        assert.deepEqual(getFacetTexts(target), ["Color", "Advanced Search"]);
        assert.deepEqual(testComponent.props.domain, []);
        assert.deepEqual(testComponent.props.groupBy, ["color"]);

        await toggleSearchBarMenu(target);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_group_by_menu .dropdown-item")),
            visibleGroupBys
        );

        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_filter_menu .dropdown-item")),
            visibleFilters
        );
    });

    QUnit.test("Several date filters and a comparison", async function (assert) {
        patchDate(2023, 3, 1, 0, 0, 0);
        serverData.views["foo,1,search"] = `
            <search>
                <filter name="date_filter" string="Date" date="date_field"/>
                <filter name="date_time_filter" string="Datetime" date="date_time_field"/>
            </search>
        `;
        const testComponent = await makeTestComponent({
            domain: [[0, "=", 1]],
            context: {
                search_default_date_filter: true,
                search_default_date_time_filter: true,
            },
        });
        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "Date: Previous Period");

        assert.deepEqual(getFacetTexts(target), [
            "Date: April 2023\nor\nDatetime: April 2023",
            "Date: Previous Period",
        ]);
        assert.deepEqual(testComponent.props.domain, [
            "&",
            [0, "=", 1],
            "&",
            ["date_time_field", ">=", "2023-03-31 23:00:00"],
            ["date_time_field", "<=", "2023-04-30 22:59:59"],
        ]);
        assert.deepEqual(testComponent.props.comparison, {
            domains: [
                {
                    arrayRepr: [
                        "&",
                        "&",
                        [0, "=", 1],
                        "&",
                        ["date_time_field", ">=", "2023-03-31 23:00:00"],
                        ["date_time_field", "<=", "2023-04-30 22:59:59"],
                        "&",
                        ["date_field", ">=", "2023-04-01"],
                        ["date_field", "<=", "2023-04-30"],
                    ],
                    description: "April 2023",
                },
                {
                    arrayRepr: [
                        "&",
                        "&",
                        [0, "=", 1],
                        "&",
                        ["date_time_field", ">=", "2023-03-31 23:00:00"],
                        ["date_time_field", "<=", "2023-04-30 22:59:59"],
                        "&",
                        ["date_field", ">=", "2023-03-01"],
                        ["date_field", "<=", "2023-03-31"],
                    ],
                    description: "March 2023",
                },
            ],
            fieldName: "date_field",
        });

        await toggleSearchBarMenu(target);
        await openAdvancedSearchDialog(target);

        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_model_field_selector_chain_part")),
            ["DateTime", "DateTime", "A date", "A date"]
        ); // 0 not found!

        await click(target, ".modal footer button:nth-child(1)");

        assert.deepEqual(testComponent.props.domain, [
            "&",
            [0, "=", 1],
            "&",
            "&",
            ["date_time_field", ">=", "2023-03-31 23:00:00"],
            ["date_time_field", "<=", "2023-04-30 22:59:59"],
            "&",
            ["date_field", ">=", "2023-04-01"],
            ["date_field", "<=", "2023-04-30"],
        ]);
    });

    QUnit.test("an invalid domain cannot be saved", async function (assert) {
        assert.expect(9);
        patchWithCleanup(odoo, {
            debug: true,
        });
        registry.category("services").add(
            "notification",
            {
                start() {
                    return {
                        add(message, options) {
                            assert.strictEqual(message, "Domain is invalid. Please correct it");
                            assert.deepEqual(options, { type: "danger" });
                        },
                    };
                },
            },
            { force: true }
        );
        const testComponent = await makeTestComponent({});
        assert.deepEqual(testComponent.props.domain, []);
        assert.deepEqual(getFacetTexts(target), []);
        assert.containsNone(target, ".modal");

        await toggleSearchBarMenu(target);
        await openAdvancedSearchDialog(target);
        assert.containsOnce(target, ".modal");

        await editInput(target, "textarea.o_domain_debug_input", "[");
        await click(target, ".modal footer button:nth-child(1)");
        assert.containsOnce(target, ".modal");
        assert.deepEqual(testComponent.props.domain, []);
        assert.deepEqual(getFacetTexts(target), []);
    });
});
