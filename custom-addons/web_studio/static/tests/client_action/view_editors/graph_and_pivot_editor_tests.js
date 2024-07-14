/** @odoo-module */

import { browser } from "@web/core/browser/browser";
import { click, getFixture, patchWithCleanup, makeDeferred } from "@web/../tests/helpers/utils";
import {
    createViewEditor,
    makeArchChanger,
    registerViewEditorDependencies,
    createMockViewResult,
    editAnySelect,
} from "@web_studio/../tests/client_action/view_editors/view_editor_tests_utils";
import { CodeEditor } from "@web/core/code_editor/code_editor";
import { onMounted } from "@odoo/owl";

/** @type {Node} */
let target;
let serverData;

QUnit.module(
    "View Editors",
    {
        async beforeEach() {
            const staticServerData = {
                models: {
                    coucou: {
                        fields: {
                            id: { string: "Id", type: "integer" },
                            display_name: { string: "Name", type: "char" },
                            m2o: { string: "Product", type: "many2one", relation: "product" },
                            char_field: { type: "char", string: "A char" },
                            priority: {
                                string: "Priority",
                                type: "selection",
                                manual: true,
                                selection: [
                                    ["1", "Low"],
                                    ["2", "Medium"],
                                    ["3", "High"],
                                ],
                            },
                        },
                        records: [],
                    },
                    product: {
                        fields: {
                            id: { string: "Id", type: "integer" },
                            display_name: { string: "Name", type: "char" },
                        },
                        records: [
                            {
                                id: 1,
                                display_name: "A very good product",
                            },
                        ],
                    },
                    partner: {
                        fields: {
                            id: { string: "Id", type: "integer" },
                            display_name: { string: "Name", type: "char" },
                            image: { string: "Image", type: "binary" },
                        },
                        records: [
                            {
                                id: 1,
                                display_name: "jean",
                                image: {},
                            },
                        ],
                    },
                },
            };

            serverData = JSON.parse(JSON.stringify(staticServerData));

            registerViewEditorDependencies();

            patchWithCleanup(browser, {
                setTimeout: (fn) => fn(),
            });

            target = getFixture();
        },
    },
    function () {
        QUnit.module("Graph");

        QUnit.test("empty graph editor", async function (assert) {
            assert.expect(3);
            serverData.models.coucou.records = [
                {
                    id: 1,
                    display_name: "coucou",
                },
            ];

            await createViewEditor({
                serverData,
                type: "graph",
                resModel: "coucou",
                arch: `<graph/>`,
            });
            assert.containsOnce(target, ".o_graph_view");
            assert.containsOnce(target, ".o_web_studio_view_renderer .o_graph_renderer");
            assert.containsOnce(
                target,
                ".o_web_studio_view_renderer .o_graph_renderer .o_graph_canvas_container canvas",
                "the graph should be a child of its container"
            );
        });

        QUnit.test("switching chart types in graph editor", async function (assert) {
            assert.expect(8);

            let editViewCount = 0;

            serverData.models.coucou.records = [
                {
                    id: 1,
                    display_name: "stage1",
                },
                {
                    id: 2,
                    display_name: "stage2",
                },
            ];

            const arch = `
                <graph string='Opportunities'>
                    <field name='display_name' type='col'/>
                    <field name='char_field' type='row'/>
                </graph>`;

            await createViewEditor({
                serverData,
                type: "graph",
                resModel: "coucou",
                arch: `<graph/>`,
                mockRPC(route, args) {
                    if (route === "/web_studio/edit_view") {
                        editViewCount++;
                        let newArch = arch;
                        if (editViewCount === 1) {
                            assert.step(args.operations[0].new_attrs.type);
                            newArch = `
                                <graph string='Opportunities' type='line'>
                                    <field name='display_name' type='col'/>
                                    <field name='char_field' type='row'/>
                                </graph>`;
                        } else if (editViewCount === 2) {
                            assert.step(args.operations[1].new_attrs.type);
                            newArch = `
                                <graph string='Opportunities' type='pie'>
                                    <field name='display_name' type='col'/>
                                    <field name='char_field' type='row'/>
                                </graph>`;
                        }
                        return createMockViewResult(serverData, "graph", newArch, "coucou");
                    }
                },
            });

            assert.strictEqual(
                target.querySelector(".o_web_studio_sidebar .o_web_studio_property_type button")
                    .textContent,
                "Bar",
                "the type field should be set to bar by default"
            );

            assert.containsOnce(
                target,
                "#stacked",
                "the stacked graph checkbox should be visible in bar chart"
            );

            // change the type field value to line chart
            await editAnySelect(
                target,
                ".o_web_studio_sidebar .o_web_studio_property_type .o_select_menu",
                "Line"
            );

            assert.verifySteps(["line"], "The requested type of graph is line");

            assert.containsNone(
                target,
                "#stacked",
                "the stacked graph checkbox should not be visible in line chart"
            );

            // change the type field value to pie chart
            await editAnySelect(
                target,
                ".o_web_studio_sidebar .o_web_studio_property_type .o_select_menu",
                "Pie"
            );

            assert.verifySteps(["pie"], "The requested type of graph is pie");
            assert.containsNone(
                target,
                "#stacked",
                "the stacked graph checkbox should not be visible in pie chart"
            );
        });

        QUnit.test("open xml editor of graph component view and close it", async function (assert) {
            assert.expect(5);

            // the XML editor button is only available in debug mode
            patchWithCleanup(odoo, { debug: true });

            // the XML editor lazy loads its libs and its templates so its start
            // method is monkey-patched to know when the widget has started
            const xmlEditorDef = makeDeferred();
            patchWithCleanup(CodeEditor.prototype, {
                setup() {
                    super.setup();
                    onMounted(() => xmlEditorDef.resolve());
                },
            });

            const arch = "<graph />";
            await createViewEditor({
                serverData,
                arch: arch,
                type: "graph",
                resModel: "coucou",
                mockRPC(route) {
                    if (route === "/web_studio/get_xml_editor_resources") {
                        return Promise.resolve({
                            views: [
                                {
                                    active: true,
                                    arch: arch,
                                    id: 1,
                                    inherit_id: false,
                                    name: "base view",
                                },
                                {
                                    active: true,
                                    arch: "<data/>",
                                    id: 42,
                                    inherit_id: 1,
                                    name: "studio view",
                                },
                            ],
                            scss: [],
                            js: [],
                        });
                    }
                },
            });

            await click(
                target.querySelector(".o_web_studio_editor .o_notebook_headers li:nth-child(2) a")
            );
            await click(target.querySelector(".o_web_studio_open_xml_editor"));
            await xmlEditorDef;
            assert.containsOnce(
                target,
                ".o_web_studio_code_editor.ace_editor",
                "the XML editor should be opened"
            );
            assert.containsNone(target, ".o_web_studio_sidebar");

            await click(
                target.querySelector(
                    ".o_web_studio_xml_resource_selector .btn-secondary:not(.dropdown-toggle)"
                )
            );
            assert.containsNone(target, ".o_ace_view_editor");
            assert.containsOnce(target, ".o_web_studio_sidebar");
            assert.containsOnce(target, ".o_graph_renderer");
        });

        QUnit.module("Pivot");

        QUnit.test("empty pivot editor", async function (assert) {
            serverData.models.coucou.records = [
                {
                    id: 1,
                    display_name: "coucou",
                },
            ];

            await createViewEditor({
                serverData,
                type: "pivot",
                resModel: "coucou",
                arch: "<pivot/>",
            });

            assert.containsOnce(target, ".o_pivot", "there should be a pivot renderer");
            assert.containsOnce(
                target,
                ".o_pivot > table",
                "the table should be the direct child of pivot"
            );

            assert.strictEqual(
                target.querySelector(".o_web_studio_sidebar .nav-link.active").textContent,
                "View"
            );
        });

        QUnit.test(
            "switching column and row groupby fields in pivot editor",
            async function (assert) {
                serverData.models.product.fields = {
                    ...serverData.models.product.fields,
                    m2o: { type: "many2one", store: true, relation: "partner" },
                    coucou_id: { type: "many2one", store: true, relation: "coucou" },
                    toughness: {
                        manual: true,
                        string: "toughness",
                        type: "selection",
                        selection: [
                            ["0", "Hard"],
                            ["1", "Harder"],
                        ],
                        store: true,
                    },
                };
                serverData.models.product.fields.display_name.store = true;
                serverData.models.product.fields.display_name.string = "display_name";

                serverData.models.partner.records = [
                    { id: 1, display_name: "jean" },
                    { id: 2, display_name: "jacques" },
                ];

                serverData.models.product.records = [
                    {
                        id: 1,
                        display_name: "xpad",
                        m2o: 2,
                    },
                    {
                        id: 2,
                        display_name: "xpod",
                    },
                ];

                const changeArch = makeArchChanger();
                const arch = `
            <pivot string='Pipeline Analysis'>
                <field name='m2o' type='col'/>
                <field name='coucou_id' type='row'/>
            </pivot>`;

                let editViewCount = 0;
                await createViewEditor({
                    type: "pivot",
                    serverData,
                    resModel: "product",
                    arch,
                    mockRPC(route, args) {
                        if (route === "/web_studio/edit_view") {
                            assert.step("edit_view");
                            editViewCount++;
                            let newArch = arch;
                            if (editViewCount === 1) {
                                assert.strictEqual(
                                    args.operations[0].target.field_names[0],
                                    "toughness",
                                    "targeted field name should be toughness"
                                );
                                newArch = `
                            <pivot>
                                <field name='m2o' type='col'/>
                                <field name='coucou_id' type='row'/>
                                <field name='toughness' type='row'/>
                            </pivot>`;
                            } else if (editViewCount === 2) {
                                assert.strictEqual(
                                    args.operations[1].target.field_names[0],
                                    "display_name",
                                    "targeted field name should be display_name"
                                );
                                newArch = `
                            <pivot string='Pipeline Analysis' colGroupBys='display_name' rowGroupBys='coucou_id,toughness'>
                                <field name='display_name' type='col'/>
                                <field name='coucou_id' type='row'/>
                                <field name='toughness' type='row'/>
                            </pivot>`;
                            } else if (editViewCount === 3) {
                                assert.strictEqual(
                                    args.operations[2].target.field_names[0],
                                    "m2o",
                                    "targeted field name should be m2o"
                                );
                                newArch = `
                            <pivot string='Pipeline Analysis' colGroupBys='display_name' rowGroupBys='m2o'>
                                <field name='display_name' type='col'/>
                                <field name='m2o' type='row'/>
                            </pivot>`;
                            }
                            changeArch(args.view_id, newArch);
                        }
                    },
                });

                assert.strictEqual(
                    target.querySelector(
                        ".o_web_studio_sidebar [name='column_groupby'] .o_select_menu"
                    ).textContent,
                    "m2o",
                    "the col field should contain correct value"
                );
                assert.strictEqual(
                    target.querySelector(
                        ".o_web_studio_sidebar [name='first_row_groupby'] .o_select_menu"
                    ).textContent,
                    "coucou_id",
                    "the row field should contain correct value"
                );

                // set the Row-Second level field value
                await editAnySelect(
                    target,
                    ".o_web_studio_sidebar [name='second_row_groupby'] .o_select_menu",
                    "toughness"
                );
                assert.verifySteps(["edit_view"]);
                assert.strictEqual(
                    target.querySelector(
                        ".o_web_studio_sidebar [name='column_groupby'] .o_select_menu"
                    ).textContent,
                    "m2o",
                    "the column field should be correctly selected"
                );
                assert.strictEqual(
                    target.querySelector(
                        ".o_web_studio_sidebar [name='first_row_groupby'] .o_select_menu"
                    ).textContent,
                    "coucou_id",
                    "the first row field should contain correct value"
                );
                assert.strictEqual(
                    target.querySelector(
                        ".o_web_studio_sidebar [name='second_row_groupby'] .o_select_menu"
                    ).textContent,
                    "toughness",
                    "the second row field should contain correct value"
                );
                assert.strictEqual(
                    $(".o_web_studio_view_renderer th").slice(0, 5).text(),
                    "TotalNonejacques",
                    "the col headers should be as expected"
                );
                assert.strictEqual(
                    $(".o_web_studio_view_renderer th").slice(8).text(),
                    "TotalNoneNone",
                    "the row headers should be as expected"
                );

                // change the column field value to Display Name
                await editAnySelect(
                    target,
                    ".o_web_studio_sidebar [name='column_groupby'] .o_select_menu",
                    "display_name"
                );
                assert.verifySteps(["edit_view"]);
                assert.strictEqual(
                    target.querySelector(
                        ".o_web_studio_sidebar [name='column_groupby'] .o_select_menu"
                    ).textContent,
                    "display_name",
                    "the column field should be correctly selected"
                );
                assert.strictEqual(
                    target.querySelector(
                        ".o_web_studio_sidebar [name='first_row_groupby'] .o_select_menu"
                    ).textContent,
                    "coucou_id",
                    "the first row field should contain correct value"
                );
                assert.strictEqual(
                    target.querySelector(
                        ".o_web_studio_sidebar [name='second_row_groupby'] .o_select_menu"
                    ).textContent,
                    "toughness",
                    "the second row field should contain correct value"
                );
                assert.strictEqual(
                    $(".o_web_studio_view_renderer th").slice(0, 5).text(),
                    "Totalxpadxpod",
                    "the col headers should be as expected"
                );
                assert.strictEqual(
                    $(".o_web_studio_view_renderer th").slice(8).text(),
                    "TotalNoneNone",
                    "the row headers should be as expected"
                );

                // change the Row-First level field value to M2O
                await editAnySelect(
                    target,
                    ".o_web_studio_sidebar [name='first_row_groupby'] .o_select_menu",
                    "m2o"
                );
                assert.verifySteps(["edit_view"]);
                assert.strictEqual(
                    target.querySelector(
                        ".o_web_studio_sidebar [name='column_groupby'] .o_select_menu"
                    ).textContent,
                    "display_name",
                    "the col field should be correctly selected"
                );
                assert.strictEqual(
                    target.querySelector(
                        ".o_web_studio_sidebar [name='first_row_groupby'] .o_select_menu"
                    ).textContent,
                    "m2o",
                    "the row field should contain correct value"
                );
                assert.strictEqual(
                    target.querySelector(
                        ".o_web_studio_sidebar [name='second_row_groupby'] .o_select_menu"
                    ).textContent,
                    "",
                    "the second row field should contain correct value"
                );
                assert.strictEqual(
                    $(".o_web_studio_view_renderer th").slice(0, 5).text(),
                    "Totalxpadxpod",
                    "the col headers should be as expected"
                );
                assert.strictEqual(
                    $(".o_web_studio_view_renderer th").slice(8).text(),
                    "TotalNonejacques",
                    "the row headers should be as expected"
                );
            }
        );

        QUnit.test("pivot measure fields domain", async function (assert) {
            serverData.models["ir.model.fields"] = {
                fields: {},
                records: [],
            };
            await createViewEditor({
                serverData,
                type: "pivot",
                resModel: "coucou",
                arch: `<pivot/>`,
                mockRPC(route, args) {
                    if (args.method === "name_search") {
                        assert.step("name_search");
                        assert.strictEqual(args.model, "ir.model.fields");
                        assert.deepEqual(args.kwargs.args, [
                            "&",
                            "&",
                            ["model", "=", "coucou"],
                            ["name", "in", ["__count"]],
                            "!",
                            ["id", "in", []],
                        ]);
                    }
                },
            });
            await click(target, ".o_field_many2many_tags input");
            assert.verifySteps(["name_search"]);
        });
    }
);
