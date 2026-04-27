/** @odoo-module */

import { browser } from "@web/core/browser/browser";
import {
    click,
    drag,
    dragAndDrop,
    editInput,
    getFixture,
    makeDeferred,
    nextTick,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";

import {
    createViewEditor,
    valueOfSelect,
    registerViewEditorDependencies,
    editAnySelect,
    createMockViewResult,
} from "@web_studio/../tests/legacy/client_action/view_editors/view_editor_tests_utils";
import { CodeEditor } from "@web/core/code_editor/code_editor";
import { registry } from "@web/core/registry";
import { PivotEditorSidebar } from "@web_studio/client_action/view_editor/editors/pivot/pivot_editor";
import { onMounted } from "@odoo/owl";

const serviceRegistry = registry.category("services");

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
                            display_name: { string: "Name", type: "char", help: "Display Name" },
                            m2o: { string: "Product", type: "many2one", relation: "product" },
                            char_field: { string: "A char", type: "char" },
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
                            product_ids: {
                                string: "Products",
                                type: "one2many",
                                relation: "product",
                            },
                        },
                        records: [
                            {
                                id: 0,
                                display_name: "Kikou petite perruche",
                            },
                            {
                                id: 1,
                                display_name: "Coucou Two",
                            },
                        ],
                    },
                    product: {
                        fields: {
                            id: { string: "Id", type: "integer" },
                            display_name: { string: "Name", type: "char" },
                        },
                        records: [
                            {
                                id: 0,
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
                                id: 0,
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
        QUnit.module("Interactive Editor Sidebar");

        QUnit.test("show properties sidepanel on field selection", async function (assert) {
            assert.expect(7);

            await createViewEditor({
                serverData,
                type: "form",
                resModel: "coucou",
                arch: `
                    <form>
                        <sheet>
                            <field name="display_name"/>
                        </sheet>
                    </form>
                `,
            });

            assert.containsOnce(
                target,
                ".o_web_studio_view_renderer .o-web-studio-editor--element-clickable",
                "there should be one node"
            );
            assert.containsOnce(
                target,
                ".o_web_studio_view_renderer .o_web_studio_hook",
                "there should be one hook"
            );

            await click(
                target,
                ".o_web_studio_view_renderer .o-web-studio-editor--element-clickable",
                true
            );
            await nextTick();

            assert.strictEqual(
                target.querySelector(".nav-link.active").innerText,
                "Properties",
                "the Properties tab should now be active"
            );

            assert.ok(
                target.querySelectorAll(".o_web_studio_property").length > 0,
                "the sidebar should now display the field properties"
            );

            assert.hasClass(
                target.querySelector(
                    ".o_web_studio_view_renderer .o-web-studio-editor--element-clickable"
                ),
                "o-web-studio-editor--element-clicked",
                "the column should have the clicked style"
            );

            assert.strictEqual(
                valueOfSelect(
                    target,
                    ".o_web_studio_sidebar .o_web_studio_property_widget .o_select_menu"
                ),
                "Text (char)",
                "the widget in sidebar should be set by default"
            );

            assert.strictEqual(
                target.querySelector(".o_web_studio_sidebar .o_web_studio_property #help").value,
                "Display Name",
                "the help tooltip in the sidebar should default to the field tooltip"
            );
        });

        QUnit.test("Sidebar should display all field's widgets", async function (assert) {
            const arch = `
                <form><sheet>
                    <group>
                        <field name="display_name"/>
                    </group>
                </sheet></form>`;

            await createViewEditor({
                serverData,
                type: "form",
                resModel: "coucou",
                arch,
            });

            await click(target.querySelector(".o_form_label"));
            await click(target.querySelector(".o_select_menu_toggler"));

            const displayedWidgetNames = [...document.querySelectorAll(".o_select_menu_item")].map(
                (x) => x.textContent
            );

            const charWidgetNames = [
                "Badge (badge)",
                "Copy Text to Clipboard (CopyClipboardChar)",
                "Copy URL to Clipboard (CopyClipboardURL)",
                "Email (email)",
                "Image (image_url)",
                "Phone (phone)",
                "Reference (reference)",
                "Text (char)",
                "Text (char_emojis)",
                "URL (url)",
            ];
            for (const name of charWidgetNames) {
                assert.ok(displayedWidgetNames.includes(name));
            }
        });

        QUnit.test("Pivot sidebar should display display name measures", async function (assert) {
            serverData.models.coucou.fields["foo"] = {
                string: "Foo",
                type: "integer",
                aggregator: "sum",
            };
            serverData.models.coucou.records[0].foo = 42;
            serverData.models.coucou.records[0].foo = 24;
            patchWithCleanup(PivotEditorSidebar.prototype, {
                get currentMeasureFields() {
                    return [1234];
                },
            });

            const arch = `
                <pivot>
                    <field name="foo" type="measure"/>
                </pivot>`;

            await createViewEditor({
                serverData,
                type: "pivot",
                resModel: "coucou",
                arch,
                mockRPC: function (route, args) {
                    if (args.method === "web_search_read" && args.model === "ir.model.fields") {
                        return {
                            records: [
                                {
                                    id: 1234,
                                    display_name: "Foo",
                                },
                            ],
                        };
                    }
                },
            });

            const badge = target.querySelector(".o_pivot_measures_fields .o_tag_badge_text");
            assert.strictEqual(badge.textContent, "Foo", "the measure name should be displayed");
        });

        QUnit.test("folds/unfolds the existing fields into sidebar", async function (assert) {
            assert.expect(10);

            const arch = `<form>
                <group>
                    <field name="display_name"/>
                </group>
            </form>`;

            await createViewEditor({
                serverData,
                type: "form",
                resModel: "coucou",
                arch,
                mockRPC: function (route) {
                    if (route === "/web_studio/edit_view") {
                        const newArch = `<form>
                            <group>
                                <field name="char_field"/>
                                <field name="display_name"/>
                            </group>
                        </form>`;
                        return createMockViewResult(serverData, "form", newArch, "coucou");
                    }
                },
            });

            assert.containsN(
                target,
                ".o_web_studio_field_type_container",
                2,
                "there should be two sections in Add (new & Components"
            );
            assert.hasClass(
                target.querySelector(".o_web_studio_existing_fields_header i"),
                "fa-caret-right",
                "should have a existing fields folded"
            );
            assert.isNotVisible(
                target.querySelector(".o_web_studio_existing_fields_section"),
                "the existing fields section should not be visible"
            );

            // Unfold the existing fields section
            await click(target.querySelector(".o_web_studio_existing_fields_header"));
            assert.containsN(
                target,
                ".o_web_studio_field_type_container",
                3,
                "there should be three sections in Add (new & existing fields & Components"
            );
            assert.hasClass(
                target.querySelector(".o_web_studio_existing_fields_header i"),
                "fa-caret-down",
                "should have a existing fields unfolded"
            );
            assert.isVisible(
                target.querySelector(".o_web_studio_existing_fields_section"),
                "the existing fields section should be visible"
            );

            // drag and drop the new char field
            await dragAndDrop(
                target.querySelector(".o_web_studio_existing_fields .o_web_studio_field_char"),
                target.querySelector(".o_inner_group .o_cell.o-draggable")
            );
            assert.isVisible(
                target.querySelector(".o_web_studio_existing_fields_section"),
                "keep the existing fields section visible when adding the new field"
            );
            // fold the existing fields section
            await click(target.querySelector(".o_web_studio_existing_fields_header"));
            assert.containsN(
                target,
                ".o_web_studio_field_type_container",
                2,
                "there should be three sections in Add (new & Components"
            );
            assert.hasClass(
                target.querySelector(".o_web_studio_existing_fields_header i"),
                "fa-caret-right",
                "should have a existing fields folded"
            );
            assert.isNotVisible(
                target.querySelector(".o_web_studio_existing_fields_section"),
                "the existing fields section should not be visible"
            );
        });

        QUnit.test("change widget binary to image", async function (assert) {
            assert.expect(4);

            const arch = `
                <form>
                    <sheet>
                        <field name='image'/>
                    </sheet>
                </form>
            `;

            serverData.models.partner.records[0].image = "kikou";

            await createViewEditor({
                serverData,
                type: "form",
                resModel: "partner",
                arch: arch,
                mockRPC: {
                    "/web_studio/edit_view": () => {
                        assert.ok("edit_view RPC has been called");
                        return createMockViewResult(serverData, "form", arch, "partner");
                    },
                },
            });

            assert.containsOnce(
                target,
                ".o_web_studio_form_view_editor .o-web-studio-editor--element-clickable",
                "there should be one binary field"
            );

            // edit the binary field
            await click(
                target,
                ".o_web_studio_form_view_editor .o-web-studio-editor--element-clickable",
                true
            );
            await nextTick();

            // Change widget from binary to image
            assert.containsOnce(
                target,
                ".o_web_studio_property_widget",
                "the sidebar should display dropdown to change widget"
            );
            assert.hasClass(
                target.querySelector(
                    ".o_web_studio_form_view_editor .o-web-studio-editor--element-clickable"
                ),
                "o-web-studio-editor--element-clicked",
                "binary field should have the clicked style"
            );

            // change widget to image
            await editAnySelect(
                target,
                ".o_web_studio_property_widget .o_select_menu",
                "Image (image)"
            );
        });

        QUnit.test("update sidebar after edition", async function (assert) {
            assert.expect(7);

            const arch = `<form><sheet>
                    <group>
                        <field name='display_name'/>
                    </group>
                    <notebook><page><field name='id'/></page></notebook>
                </sheet></form>`;
            await createViewEditor({
                serverData,
                type: "form",
                resModel: "coucou",
                arch: arch,
                mockRPC: {
                    "/web_studio/edit_view": () => {
                        assert.strictEqual(
                            target.querySelector(".o_web_studio_sidebar input[name=string]").value,
                            "test",
                            "new input value is set in the sidebar"
                        );
                        assert.step("editView");
                        return createMockViewResult(serverData, "form", arch, "partner");
                    },
                },
            });

            // rename field
            await click(target.querySelector('[name="display_name"]').parentElement);
            assert.containsOnce(
                target,
                ".o_wrap_label.o-web-studio-editor--element-clicked[data-field-name=display_name]"
            );
            assert.strictEqual(
                target.querySelector(".o_web_studio_sidebar input[name=string]").value,
                "Name",
                "initial input value is the correct one"
            );

            await editInput(target, '.o_web_studio_sidebar input[name="string"]', "test");
            assert.containsOnce(
                target,
                ".o_wrap_label.o-web-studio-editor--element-clicked[data-field-name=display_name]"
            );
            // The name stay the same because on the mockRPC we return the same view.
            assert.strictEqual(
                target.querySelector(".o_web_studio_sidebar input[name=string]").value,
                "Name",
                "input value has been updated in the sidebar"
            );
            assert.verifySteps(["editView"], "should have edit the view 1 time");
        });

        QUnit.test("default value in sidebar", async function (assert) {
            assert.expect(3);

            const arch = `<form><sheet>
                    <group>
                        <field name='display_name'/>
                        <field name='priority'/>
                    </group>
                </sheet></form>`;
            await createViewEditor({
                serverData,
                type: "form",
                resModel: "coucou",
                arch: arch,
                mockRPC: {
                    "/web_studio/get_default_value": (route, args) => {
                        if (args.field_name === "display_name") {
                            return Promise.resolve({ default_value: "yolo" });
                        } else if (args.field_name === "priority") {
                            return Promise.resolve({ default_value: "1" });
                        }
                    },
                },
            });

            await click(target.querySelector('[name="display_name"]').parentElement);
            assert.strictEqual(
                target.querySelector('.o_web_studio_property input[name="default_value"]').value,
                "yolo",
                "the sidebar should now display the field properties"
            );

            await click(target.querySelector('[name="priority"]').parentElement);
            await click(
                target.querySelector(
                    ".o_web_studio_property_default_value .o_select_menu_toggler_slot"
                )
            );
            assert.strictEqual(
                target.querySelector(
                    ".o_web_studio_property_default_value .o_select_menu_toggler_slot"
                ).textContent,
                "Low",
                "the sidebar should display the correct default value"
            );
            assert.strictEqual(
                target.querySelector(".o_select_menu_menu").textContent,
                "HighLowMedium",
                "the sidebar should have the right options"
            );
        });

        QUnit.test("default value in sidebar according to field type", async function (assert) {
            const arch = `<form><sheet>
                    <group>
                        <field name='display_name'/>
                        <field name='priority' widget="radio"/>
                    </group>
                </sheet></form>`;
            await createViewEditor({
                serverData,
                type: "form",
                resModel: "coucou",
                arch: arch,
                mockRPC: {
                    "/web_studio/get_default_value": (route, args) => {
                        if (args.field_name === "priority") {
                            return Promise.resolve({ default_value: "1" });
                        }
                    },
                },
            });

            assert.containsN(target, '.o_field_widget[name="priority"] input[type="radio"]', 3);
            await click(target.querySelector('.o_field_widget[name="priority"]'));
            await click(
                target.querySelector(
                    ".o_web_studio_property_default_value .o_select_menu_toggler_slot"
                )
            );
            assert.strictEqual(
                target.querySelector(
                    ".o_web_studio_property_default_value .o_select_menu_toggler_slot"
                ).textContent,
                "Low",
                "the sidebar should display the correct default value"
            );
            assert.containsOnce(target, ".o-dropdown--menu");
            assert.strictEqual(
                target.querySelector(".o-dropdown--menu").textContent,
                "HighLowMedium",
                "the sidebar should have the right options"
            );
        });

        QUnit.test("default value for new field name", async function (assert) {
            assert.expect(2);

            let editViewCount = 0;
            const arch = `<form><sheet>
                <group>
                <field name='display_name'/>
                </group>
                </sheet></form>`;
            await createViewEditor({
                serverData,
                type: "form",
                resModel: "coucou",
                arch: arch,
                mockRPC: {
                    "/web_studio/edit_view": (route, args) => {
                        editViewCount++;
                        // new field default name should be x_studio_[FieldType]_field_[RandomString]
                        if (editViewCount === 1) {
                            assert.ok(
                                args.operations[0].node.field_description.name.startsWith(
                                    "x_studio_char_field_"
                                ),
                                "default new field name should start with x_studio_char_field_*"
                            );
                        } else if (editViewCount === 2) {
                            assert.ok(
                                args.operations[1].node.field_description.name.startsWith(
                                    "x_studio_float_field_"
                                ),
                                "default new field name should start with x_studio_float_field_*"
                            );
                        }
                        return createMockViewResult(serverData, "form", arch, "partner");
                    },
                },
            });

            await dragAndDrop(
                target.querySelector(".o_web_studio_new_fields .o_web_studio_field_char"),
                target.querySelector(".o_inner_group .o_cell.o-draggable")
            );
            await dragAndDrop(
                target.querySelector(".o_web_studio_new_fields .o_web_studio_field_float"),
                target.querySelector(".o_inner_group .o_cell.o-draggable")
            );
        });

        QUnit.test("remove starting underscore from new field value", async function (assert) {
            assert.expect(1);
            // renaming is only available in debug mode
            patchWithCleanup(odoo, { debug: true });

            const arch = `<form><sheet>
                <group>
                <field name="display_name"/>
                </group>
                </sheet></form>`;
            await createViewEditor({
                serverData,
                type: "form",
                resModel: "coucou",
                arch: arch,
                mockRPC: {
                    "/web_studio/edit_view": (route, args) => {
                        const fieldName = args.operations[0].node.field_description.name;
                        const arch = `<form><sheet><group><field name='${fieldName}'/><field name='display_name'/></group></sheet></form>`;
                        serverData.models.coucou.fields[fieldName] = {
                            string: "Hello",
                            type: "char",
                        };
                        return createMockViewResult(serverData, "form", arch, "partner");
                    },
                    "/web_studio/rename_field": () => {
                        // random value returned in order for the mock server to know that this route is implemented.
                        return true;
                    },
                },
            });

            await dragAndDrop(
                target.querySelector(".o_web_studio_new_fields .o_web_studio_field_char"),
                target.querySelector(".o_inner_group .o_cell.o-draggable")
            );
            await nextTick();

            // rename the field
            await editInput(target, '.o_web_studio_property input[name="technical_name"]', "__new");
            assert.strictEqual(
                target.querySelector(".o_web_studio_property input[name='technical_name']").value,
                "new",
                "value should not contain starting underscore in new field"
            );
        });

        QUnit.test("notebook and group not drag and drop in a group", async function (assert) {
            assert.expect(2);

            const arch = `<form><sheet>
                    <group>
                        <group>
                            <field name='display_name'/>
                        </group>
                        <group>
                        </group>
                    </group>
                </sheet></form>`;
            await createViewEditor({
                serverData,
                type: "form",
                resModel: "coucou",
                arch: arch,
                mockRPC: {
                    "/web_studio/edit_view": () => {
                        assert.step("editView");
                    },
                },
            });

            await dragAndDrop(
                target.querySelector(".o_web_studio_field_type_container .o_web_studio_field_tabs"),
                target.querySelector(".o_group .o_cell.o-draggable")
            );
            assert.verifySteps([], "the notebook cannot be dropped inside a group");
            await dragAndDrop(
                target.querySelector(
                    ".o_web_studio_field_type_container .o_web_studio_field_columns"
                ),
                target.querySelector(".o_group .o_cell.o-draggable")
            );
            assert.verifySteps([], "the group cannot be dropped inside a group");
        });

        QUnit.test(
            "moving a field outside of a group doesn't have a highlight",
            async function (assert) {
                assert.expect(2);

                await createViewEditor({
                    serverData,
                    type: "form",
                    resModel: "coucou",
                    arch: `<form>
                            <sheet>
                                <div class='notInAGroup' style='width:50px;height:50px'/>
                                <group>
                                    <div class='inAGroup' style='width:50px;height:50px'/>
                                </group>
                            </sheet>
                        </form>
                `,
                });

                const drag1 = await drag(
                    target.querySelector(".o_web_studio_new_fields .o_web_studio_field_monetary")
                );
                await drag1.moveTo(target.querySelector(".notInAGroup"));
                assert.containsNone(
                    target,
                    ".o_web_studio_nearest_hook",
                    "There should be no highlighted hook"
                );
                await drag1.cancel();

                const drag2 = await drag(
                    target.querySelector(".o_web_studio_new_fields .o_web_studio_field_monetary")
                );
                await drag2.moveTo(target.querySelector(".inAGroup"));
                assert.containsOnce(
                    target,
                    ".o_web_studio_nearest_hook",
                    "There should be the highlighted hook"
                );

                await drag2.cancel();
            }
        );

        QUnit.test('click on the "More" Button', async function (assert) {
            assert.expect(3);

            // the 'More' button is only available in debug mode
            patchWithCleanup(odoo, { debug: true });

            const openFormAction = {
                res_id: 99999999,
                res_model: "ir.ui.view",
                target: "current",
                type: "ir.actions.act_window",
                views: [[false, "form"]],
            };

            const fakeActionService = {
                start() {
                    return {
                        async doAction(action, options) {
                            assert.deepEqual(
                                action,
                                openFormAction,
                                "action service must receive the doAction call"
                            );
                            assert.strictEqual(options.clearBreadcrumbs, true);
                            return true;
                        },
                    };
                },
            };
            serviceRegistry.add("action", fakeActionService, { force: true });

            const arch = `
            <form>
                <sheet>
                    <field name='display_name'/>
                    <field name='product_ids'>
                        <list><field name='display_name'/></list>
                    </field>
                </sheet>
            </form>`;

            await createViewEditor({
                serverData,
                arch,
                type: "form",
                resModel: "coucou",
            });

            await click(
                target.querySelector(".o_web_studio_editor .o_notebook_headers li:nth-child(2) a")
            );
            assert.containsOnce(
                target,
                ".o_web_studio_sidebar .o_web_studio_parameters",
                "there should be the button to go to the ir.ui.view form"
            );

            await click(target.querySelector(".o_web_studio_sidebar .o_web_studio_parameters"));
        });

        QUnit.test('click on the "More" Button in reified field', async function (assert) {
            assert.expect(2);

            serverData.models.coucou.fields.sel_groups_10 = {
                string: "Group sel",
                type: "selection",
                manual: true,
                selection: [
                    ["1", "Low"],
                    ["2", "Medium"],
                    ["3", "High"],
                ],
            };

            // the 'More' button is only available in debug mode
            patchWithCleanup(odoo, { debug: true });

            const arch = `
            <form>
                <sheet>
                    <field name='display_name'/>
                    <field name='sel_groups_10'/>
                </sheet>
            </form>`;

            await createViewEditor({
                serverData,
                arch,
                type: "form",
                resModel: "coucou",
            });

            await click(target.querySelector('[name="sel_groups_10"]'));
            assert.containsOnce(
                target,
                ".o_web_studio_sidebar .o_web_studio_parameters",
                "there should be the button to go to the ir.ui.view form"
            );

            await click(target.querySelector(".o_web_studio_sidebar .o_web_studio_parameters"));
            assert.strictEqual(
                target.querySelector(".o_dialog .modal-body").textContent,
                "You cannot perform this action on this field.",
                "there should be a dialog preventing the users from accessing field properties"
            );
        });

        QUnit.test("open xml editor of component view", async function (assert) {
            assert.expect(1);

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

            const arch = "<pivot />";
            await createViewEditor({
                serverData,
                arch: arch,
                type: "pivot",
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
        });
    }
);
