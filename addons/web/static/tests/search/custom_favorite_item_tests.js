/** @odoo-module **/

import { getFixture, patchWithCleanup, triggerEvent } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";
import { dialogService } from "@web/core/dialog/dialog_service";
import { registry } from "@web/core/registry";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { FavoriteMenu } from "@web/search/favorite_menu/favorite_menu";
import { useSetupAction } from "@web/webclient/actions/action_hook";
import {
    editFavoriteName,
    editSearch,
    getFacetTexts,
    makeWithSearch,
    saveFavorite,
    setupControlPanelFavoriteMenuRegistry,
    setupControlPanelServiceRegistry,
    toggleFavoriteMenu,
    toggleSaveFavorite,
    validateSearch,
} from "./helpers";

const { Component, xml } = owl;
const serviceRegistry = registry.category("services");

/**
 * @param {HTMLElement} target
 */
async function toggleDefaultCheckBox(target) {
    const checkbox = target.querySelector("input[type='checkbox']");
    checkbox.checked = !checkbox.checked;
    await triggerEvent(checkbox, null, "change");
}

/**
 * @param {HTMLElement} target
 */
async function toggleShareCheckBox(target) {
    const checkbox = target.querySelectorAll("input[type='checkbox']")[1];
    checkbox.checked = !checkbox.checked;
    await triggerEvent(checkbox, null, "change");
}

let target;
let serverData;
QUnit.module("Search", (hooks) => {
    hooks.beforeEach(async () => {
        serverData = {
            models: {
                foo: {
                    fields: {
                        bar: { string: "Bar", type: "many2one", relation: "partner" },
                        birthday: { string: "Birthday", type: "date", store: true, sortable: true },
                        date_field: { string: "Date", type: "date", store: true, sortable: true },
                        float_field: { string: "Float", type: "float", group_operator: "sum" },
                        foo: { string: "Foo", type: "char", store: true, sortable: true },
                    },
                    records: {},
                },
            },
            views: {
                "foo,false,search": `<search/>`,
            },
        };
        setupControlPanelFavoriteMenuRegistry();
        setupControlPanelServiceRegistry();
        serviceRegistry.add("dialog", dialogService);
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout: () => {},
        });

        target = getFixture();
    });

    QUnit.module("CustomFavoriteItem");

    QUnit.test("simple rendering", async function (assert) {
        assert.expect(3);

        await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchMenuTypes: ["favorite"],
            searchViewId: false,
            config: {
                getDisplayName: () => "Action Name",
            },
        });

        await toggleFavoriteMenu(target);
        await toggleSaveFavorite(target);
        assert.strictEqual(
            target.querySelector('.o_add_favorite input[type="text"]').value,
            "Action Name"
        );
        assert.containsN(target, '.o_add_favorite .custom-checkbox input[type="checkbox"]', 2);
        const labelEls = target.querySelectorAll(".o_add_favorite .custom-checkbox label");
        assert.deepEqual(
            [...labelEls].map((e) => e.innerText.trim()),
            ["Use by default", "Share with all users"]
        );
    });

    QUnit.test("favorites use by default and share are exclusive", async function (assert) {
        assert.expect(11);

        await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchMenuTypes: ["favorite"],
            searchViewId: false,
        });

        await toggleFavoriteMenu(target);
        await toggleSaveFavorite(target);
        const checkboxes = target.querySelectorAll('input[type="checkbox"]');

        assert.strictEqual(checkboxes.length, 2, "2 checkboxes are present");

        assert.notOk(checkboxes[0].checked, "Start: None of the checkboxes are checked (1)");
        assert.notOk(checkboxes[1].checked, "Start: None of the checkboxes are checked (2)");

        await toggleDefaultCheckBox(target);

        assert.ok(checkboxes[0].checked, "The first checkbox is checked");
        assert.notOk(checkboxes[1].checked, "The second checkbox is not checked");

        await toggleShareCheckBox(target);

        assert.notOk(
            checkboxes[0].checked,
            "Clicking on the second checkbox checks it, and unchecks the first (1)"
        );
        assert.ok(
            checkboxes[1].checked,
            "Clicking on the second checkbox checks it, and unchecks the first (2)"
        );

        await toggleDefaultCheckBox(target);

        assert.ok(
            checkboxes[0].checked,
            "Clicking on the first checkbox checks it, and unchecks the second (1)"
        );
        assert.notOk(
            checkboxes[1].checked,
            "Clicking on the first checkbox checks it, and unchecks the second (2)"
        );

        await toggleDefaultCheckBox(target);

        assert.notOk(checkboxes[0].checked, "End: None of the checkboxes are checked (1)");
        assert.notOk(checkboxes[1].checked, "End: None of the checkboxes are checked (2)");
    });

    QUnit.test("save filter", async function (assert) {
        assert.expect(4);

        class TestComponent extends Component {
            setup() {
                useSetupAction({
                    getContext: () => {
                        return { someKey: "foo" };
                    },
                });
            }
        }
        TestComponent.components = { FavoriteMenu };
        TestComponent.template = xml`<div><FavoriteMenu/></div>`;

        const comp = await makeWithSearch({
            serverData,
            mockRPC: (_, args) => {
                if (args.model === "ir.filters" && args.method === "create_or_replace") {
                    const irFilter = args.args[0];
                    assert.deepEqual(irFilter.context, { group_by: [], someKey: "foo" });
                    return 7; // fake serverSideId
                }
            },
            resModel: "foo",
            context: { someOtherKey: "bar" }, // should not end up in filter's context
            Component: TestComponent,
            searchViewId: false,
        });
        comp.env.bus.on("CLEAR-CACHES", comp, () => assert.step("CLEAR-CACHES"));

        assert.verifySteps([]);

        await toggleFavoriteMenu(target);
        await toggleSaveFavorite(target);
        await editFavoriteName(target, "aaa");
        await saveFavorite(target);

        assert.verifySteps(["CLEAR-CACHES"]);
    });

    QUnit.test("dynamic filters are saved dynamic", async function (assert) {
        assert.expect(3);

        await makeWithSearch({
            serverData,
            mockRPC: (_, args) => {
                if (args.model === "ir.filters" && args.method === "create_or_replace") {
                    const irFilter = args.args[0];
                    assert.deepEqual(
                        irFilter.domain,
                        '[("date_field", ">=", (context_today() + relativedelta()).strftime("%Y-%m-%d"))]'
                    );
                    return 7; // fake serverSideId
                }
            },
            resModel: "foo",
            Component: ControlPanel,
            searchMenuTypes: ["favorite"],
            searchViewId: false,
            searchViewArch: `
                    <search>
                        <filter string="Filter" name="filter" domain="[('date_field', '>=', (context_today() + relativedelta()).strftime('%Y-%m-%d'))]"/>
                    </search>
                `,
            context: { search_default_filter: 1 },
        });

        assert.deepEqual(getFacetTexts(target), ["Filter"]);

        await toggleFavoriteMenu(target);
        await toggleSaveFavorite(target);
        await editFavoriteName(target, "My favorite");
        await saveFavorite(target);

        assert.deepEqual(getFacetTexts(target), ["My favorite"]);
    });

    QUnit.test("save filters created via autocompletion works", async function (assert) {
        assert.expect(4);

        await makeWithSearch({
            serverData,
            mockRPC: (_, args) => {
                if (args.model === "ir.filters" && args.method === "create_or_replace") {
                    const irFilter = args.args[0];
                    assert.deepEqual(irFilter.domain, '[("foo", "ilike", "a")]');
                    return 7; // fake serverSideId
                }
            },
            resModel: "foo",
            Component: ControlPanel,
            searchMenuTypes: ["favorite"],
            searchViewId: false,
            searchViewArch: `
                    <search>
                        <field name="foo"/>
                    </search>
                `,
        });

        assert.deepEqual(getFacetTexts(target), []);

        await editSearch(target, "a");
        await validateSearch(target);

        assert.deepEqual(getFacetTexts(target), ["Foo\na"]);

        await toggleFavoriteMenu(target);
        await toggleSaveFavorite(target);
        await editFavoriteName(target, "My favorite");
        await saveFavorite(target);

        assert.deepEqual(getFacetTexts(target), ["My favorite"]);
    });

    QUnit.test(
        "favorites have unique descriptions (the submenus of the favorite menu are correctly updated)",
        async function (assert) {
            assert.expect(5);

            serviceRegistry.add(
                "notification",
                {
                    start() {
                        return {
                            add(message, options) {
                                assert.strictEqual(
                                    message,
                                    "A filter with same name already exists."
                                );
                                assert.deepEqual(options, { type: "danger" });
                            },
                        };
                    },
                },
                { force: true }
            );

            await makeWithSearch({
                serverData,
                mockRPC: (route, args) => {
                    if (args.model === "ir.filters" && args.method === "create_or_replace") {
                        const irFilter = args.args[0];
                        assert.deepEqual(irFilter, {
                            action_id: false,
                            context: { group_by: [] },
                            domain: "[]",
                            is_default: false,
                            model_id: "foo",
                            name: "My favorite 2",
                            sort: "[]",
                            user_id: 7,
                        });
                        return 2; // serverSideId
                    }
                },
                resModel: "foo",
                Component: ControlPanel,
                searchMenuTypes: ["favorite"],
                searchViewId: false,
                irFilters: [
                    {
                        context: "{}",
                        domain: "[]",
                        id: 1,
                        is_default: false,
                        name: "My favorite",
                        sort: "[]",
                        user_id: [2, "Mitchell Admin"],
                    },
                ],
            });

            await toggleFavoriteMenu(target);
            await toggleSaveFavorite(target);

            // first try: should fail
            await editFavoriteName(target, "My favorite");
            await saveFavorite(target);

            // second try: should succeed
            await editFavoriteName(target, "My favorite 2");
            await saveFavorite(target);

            // third try: should fail
            await editFavoriteName(target, "My favorite 2");
            await saveFavorite(target);
        }
    );

    QUnit.skip("save search filter in modal", async function (assert) {
        /** @todo I don't know yet how to convert this test */
        // assert.expect(5);
        // serverData.models = {
        //     partner: {
        //         fields: {
        //             date_field: {
        //                 string: "Date",
        //                 type: "date",
        //                 store: true,
        //                 sortable: true,
        //                 searchable: true,
        //             },
        //             birthday: { string: "Birthday", type: "date", store: true, sortable: true },
        //             foo: { string: "Foo", type: "char", store: true, sortable: true },
        //             bar: { string: "Bar", type: "many2one", relation: "partner" },
        //             float_field: { string: "Float", type: "float", group_operator: "sum" },
        //         },
        //         records: [
        //             {
        //                 id: 1,
        //                 display_name: "First record",
        //                 foo: "yop",
        //                 bar: 2,
        //                 date_field: "2017-01-25",
        //                 birthday: "1983-07-15",
        //                 float_field: 1,
        //             },
        //             {
        //                 id: 2,
        //                 display_name: "Second record",
        //                 foo: "blip",
        //                 bar: 1,
        //                 date_field: "2017-01-24",
        //                 birthday: "1982-06-04",
        //                 float_field: 2,
        //             },
        //             {
        //                 id: 3,
        //                 display_name: "Third record",
        //                 foo: "gnap",
        //                 bar: 1,
        //                 date_field: "2017-01-13",
        //                 birthday: "1985-09-13",
        //                 float_field: 1.618,
        //             },
        //             {
        //                 id: 4,
        //                 display_name: "Fourth record",
        //                 foo: "plop",
        //                 bar: 2,
        //                 date_field: "2017-02-25",
        //                 birthday: "1983-05-05",
        //                 float_field: -1,
        //             },
        //             {
        //                 id: 5,
        //                 display_name: "Fifth record",
        //                 foo: "zoup",
        //                 bar: 2,
        //                 date_field: "2016-01-25",
        //                 birthday: "1800-01-01",
        //                 float_field: 13,
        //             },
        //             { id: 7, display_name: "Partner 6" },
        //             { id: 8, display_name: "Partner 7" },
        //             { id: 9, display_name: "Partner 8" },
        //             { id: 10, display_name: "Partner 9" },
        //         ],
        //     },
        // };
        // const form = await createView({
        //     arch: `
        //     <form string="Partners">
        //         <sheet>
        //             <group>
        //                 <field name="bar"/>
        //             </group>
        //         </sheet>
        //     </form>`,
        //     archs: {
        //         "partner,false,list": '<tree><field name="display_name"/></tree>',
        //         "partner,false,search": '<search><field name="date_field"/></search>',
        //     },
        //     data,
        //     model: "partner",
        //     res_id: 1,
        //     View: FormView,
        //     env: {
        //         dataManager: {
        //             create_filter(filter) {
        //                 assert.strictEqual(
        //                     filter.name,
        //                     "Awesome Test Customer Filter",
        //                     "filter name should be correct"
        //                 );
        //             },
        //         },
        //     },
        // });
        // await testUtils.form.clickEdit(form);
        // await testUtils.fields.many2one.clickOpenDropdown("bar");
        // await testUtils.fields.many2one.clickItem("bar", "Search");
        // assert.containsN(document.body, "tr.o_data_row", 9, "should display 9 records");
        // await toggleFilterMenu(".modal");
        // await toggleAddCustomFilter(".modal");
        // assert.strictEqual(
        //     document.querySelector(".o_filter_condition select.o_generator_menu_field").value,
        //     "date_field",
        //     "date field should be selected"
        // );
        // await applyFilter(".modal");
        // assert.containsNone(document.body, "tr.o_data_row", "should display 0 records");
        // // Save this search
        // await toggleFavoriteMenu(".modal");
        // await toggleSaveFavorite(".modal");
        // const filterNameInput = document.querySelector('.o_add_favorite input[type="text"]');
        // assert.isVisible(filterNameInput, "should display an input field for the filter name");
        // await testUtils.fields.editInput(filterNameInput, "Awesome Test Customer Filter");
        // await click(document.querySelector(".o_add_favorite button.btn-primary"));
        // form.destroy();
    });
});
