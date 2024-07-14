/** @odoo-module */

import { browser } from "@web/core/browser/browser";
import {
    click,
    editInput,
    getFixture,
    nextTick,
    patchWithCleanup,
    triggerEvent,
    dragAndDrop,
    selectDropdownItem,
} from "@web/../tests/helpers/utils";
import {
    createMockViewResult,
    createViewEditor,
    registerViewEditorDependencies,
    editAnySelect,
    makeArchChanger,
} from "@web_studio/../tests/client_action/view_editors/view_editor_tests_utils";
import { registry } from "@web/core/registry";
import { disableHookAnimation, selectorContains } from "./view_editor_tests_utils";
import { createEnterpriseWebClient } from "@web_enterprise/../tests/helpers";
import { doAction } from "@web/../tests/webclient/helpers";
import { openStudio } from "../../helpers";
import { session } from "@web/session";
import { ListRenderer } from "@web/views/list/list_renderer";
import { ListEditorRenderer } from "@web_studio/client_action/view_editor/editors/list/list_editor_renderer";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { SIDEBAR_SAFE_FIELDS } from "@web_studio/client_action/view_editor/editors/sidebar_safe_fields";
import { onWillRender } from "@odoo/owl";

/** @type {Node} */
let target;
let serverData;

function currentSidebarTab() {
    return target.querySelector(".o_web_studio_sidebar .nav-link.active").innerText;
}

function showNewTab() {
    return click(target, ".o_web_studio_sidebar li:nth-child(1) a");
}

function showViewTab() {
    return click(target, ".o_web_studio_sidebar li:nth-child(2) a");
}

async function unfoldExistingFieldsSection() {
    const result = target.querySelectorAll(".o_web_studio_existing_fields .o_web_studio_component");
    if (result.length === 0) {
        return click(target, ".o_web_studio_existing_fields_header");
    }
}

function setFieldAvailableInSidebar(key) {
    const sideBarPushedIndex = SIDEBAR_SAFE_FIELDS.push(key) - 1;
    registerCleanup(() => {
        SIDEBAR_SAFE_FIELDS.splice(sideBarPushedIndex, 1);
    });
}

const defaultMockRpc = {
    "/web/dataset/call_kw/res.users/has_group": () => true,
};

QUnit.module(
    "View Editors",
    {
        async beforeEach() {
            serverData = {
                models: {
                    coucou: {
                        fields: {
                            id: { string: "Id", type: "integer" },
                            display_name: { string: "Name", type: "char" },
                            m2o: { string: "Product", type: "many2one", relation: "product" },
                            char_field: { type: "char", string: "A char" },
                            croissant: { string: "Croissant", type: "integer" },
                            float_field: { string: "Float", type: "float" },
                            money_field: { string: "Money", type: "monetary" },
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
                                id: 1,
                                display_name: "Kikou petite perruche",
                            },
                            {
                                id: 2,
                                display_name: "Coucou Two",
                            },
                        ],
                    },
                    product: {
                        fields: {
                            id: { string: "Id", type: "integer" },
                            display_name: { string: "Name", type: "char" },
                            toughness: {
                                manual: true,
                                string: "toughness",
                                type: "selection",
                                selection: [
                                    ["0", "Hard"],
                                    ["1", "Harder"],
                                ],
                            },
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

            registerViewEditorDependencies();

            patchWithCleanup(browser, {
                setTimeout: (fn) => fn(),
            });

            target = getFixture();
        },
    },
    function () {
        QUnit.module("List");

        QUnit.test("list editor sidebar", async function (assert) {
            assert.expect(5);

            await createViewEditor({
                serverData,
                resModel: "coucou",
                type: "list",
                arch: "<tree/>",
                mockRPC: {
                    "/web/dataset/call_kw/coucou/web_search_read": () => {
                        return {
                            records: [],
                            length: 0,
                        };
                    },
                },
            });

            assert.containsOnce(target, ".o_web_studio_sidebar", "there should be a sidebar");
            assert.strictEqual(
                currentSidebarTab(),
                "Add",
                "the Add tab should be active in list view"
            );
            assert.containsN(
                target,
                ".o_web_studio_sidebar .tab-pane h3",
                2,
                "there should be two sections in Add (new & existing fields)"
            );

            assert.hasClass(
                target.querySelector(".nav-tabs > li:nth-child(3)"),
                "disabled",
                "the Properties tab should be disabled"
            );

            await click(target.querySelector(".nav-tabs > li:nth-child(2) a"));

            assert.strictEqual(
                currentSidebarTab(),
                "View",
                "the View tab should be active in list view"
            );
        });

        QUnit.test("empty list editor", async function (assert) {
            assert.expect(4);

            await createViewEditor({
                type: "list",
                serverData: serverData,
                resModel: "coucou",
                arch: "<tree/>",
                mockRPC: defaultMockRpc,
            });

            assert.containsOnce(
                target,
                ".o_web_studio_list_view_editor",
                "there should be a list editor"
            );
            assert.containsOnce(
                target,
                ".o_web_studio_list_view_editor table thead th.o_web_studio_hook",
                "there should be one hook"
            );
            assert.containsNone(
                target,
                ".o_web_studio_list_view_editor [data-studio-xpath]",
                "there should be no node"
            );

            await unfoldExistingFieldsSection();

            const fieldsCount = Object.keys(serverData.models.coucou.fields).length;
            assert.containsN(
                target,
                ".o_web_studio_sidebar .o_web_studio_existing_fields .o_web_studio_component",
                fieldsCount,
                "all fields should be available"
            );
        });

        QUnit.test("search existing fields into sidebar", async function (assert) {
            assert.expect(6);

            await createViewEditor({
                serverData,
                resModel: "coucou",
                type: "list",
                arch: "<tree/>",
                mockRPC: {
                    "/web/dataset/call_kw/coucou/web_search_read": () => ({
                        records: [],
                        length: 0,
                    }),
                },
            });

            assert.containsOnce(target, ".o_web_studio_sidebar", "there should be a sidebar");
            assert.strictEqual(
                currentSidebarTab(),
                "Add",
                "the Add tab should be active in list view"
            );
            assert.containsN(
                target,
                ".o_web_studio_sidebar .tab-pane h3",
                2,
                "there should be two sections in Add (new & existing fields)"
            );

            await unfoldExistingFieldsSection();

            const setSearchInput = async (value) =>
                editInput(target, ".o_web_studio_sidebar_search_input", value);

            const fieldsCount = Object.keys(serverData.models.coucou.fields).length;
            assert.containsN(
                target,
                ".o_web_studio_existing_fields .o_web_studio_component",
                fieldsCount
            );

            await setSearchInput("id");
            assert.containsN(target, ".o_web_studio_existing_fields .o_web_studio_component", 1);

            await setSearchInput("coucou");
            assert.containsNone(target, ".o_web_studio_existing_fields .o_web_studio_component");
        });

        QUnit.test("list editor", async function (assert) {
            await createViewEditor({
                serverData,
                resModel: "coucou",
                type: "list",
                arch: "<tree><field name='display_name'/></tree>",
                mockRPC: defaultMockRpc,
            });

            assert.containsOnce(
                target,
                ".o_web_studio_list_view_editor table thead [data-studio-xpath]",
                "there should be one head node"
            );
            assert.containsN(
                target,
                "table thead th.o_web_studio_hook",
                2,
                "there should be two hooks (before & after the field)"
            );

            await unfoldExistingFieldsSection();

            // Number of fields minus the display_name as it should not be available
            const fieldsCount = Object.keys(serverData.models.coucou.fields).length - 1;
            assert.containsN(
                target,
                ".o_web_studio_sidebar .o_web_studio_existing_fields .o_web_studio_component",
                fieldsCount,
                "fields that are not already in the view should be available"
            );

            assert.containsN(target, "thead th", 3);
            assert.containsN(target, "tbody tr", 4);

            const recordsCount = serverData.models.coucou.records.length;
            assert.containsN(target, "tbody td.o_data_cell", recordsCount);

            target.querySelectorAll("tbody tr:not(.o_data_row) td").forEach((el) => {
                assert.strictEqual(el.getAttribute("colspan"), "3");
            });

            assert.containsN(target, "tfoot td", 3);
        });

        QUnit.test("disable optional field dropdown icon", async function (assert) {
            assert.expect(3);

            await createViewEditor({
                serverData,
                resModel: "coucou",
                type: "list",
                arch: "<tree><field name='display_name' optional='show'/></tree>",
                mockRPC: defaultMockRpc,
            });

            assert.containsOnce(
                target,
                "i.o_optional_columns_dropdown_toggle",
                "there should be optional field dropdown icon"
            );
            assert.hasClass(
                target.querySelector("i.o_optional_columns_dropdown_toggle"),
                "text-muted",
                "optional field dropdown icon must be muted"
            );

            await click(target.querySelector("i.o_optional_columns_dropdown_toggle"));
            assert.containsNone(target, ".o-dropdown--menu");
        });

        QUnit.test("optional field in list editor", async function (assert) {
            assert.expect(1);

            await createViewEditor({
                serverData,
                resModel: "coucou",
                type: "list",
                arch: '<tree><field name="display_name"/></tree>',
                mockRPC: defaultMockRpc,
            });

            await click(target.querySelector(".o_web_studio_view_renderer [data-studio-xpath]"));
            assert.containsOnce(
                target,
                ".o_web_studio_sidebar .o_web_studio_property_optional",
                'there should be an "optional" field in the properties tab'
            );
        });

        QUnit.test(
            'new field should come with "show" as default value of optional',
            async function (assert) {
                assert.expect(1);

                const arch = "<tree><field name='display_name'/></tree>";
                await createViewEditor({
                    serverData,
                    resModel: "coucou",
                    type: "list",
                    arch,
                    mockRPC: {
                        ...defaultMockRpc,
                        "/web_studio/edit_view": (route, args) => {
                            assert.strictEqual(
                                args.operations[0].node.attrs.optional,
                                "show",
                                "default value of optional should be 'show'"
                            );
                            return createMockViewResult(serverData, "list", arch, "coucou");
                        },
                    },
                });

                await dragAndDrop(
                    ".o_web_studio_new_fields .o_web_studio_field_char",
                    ".o_web_studio_hook",
                    "top"
                );
                await nextTick();
            }
        );

        QUnit.test("new field before a button_group", async function (assert) {
            assert.expect(3);

            const arch = `
                <tree>
                    <button name="action_1" type="object"/>
                    <button name="action_2" type="object"/>
                    <field name='display_name'/>
                </tree>
            `;
            await createViewEditor({
                serverData,
                type: "list",
                resModel: "coucou",
                arch,
                mockRPC: {
                    ...defaultMockRpc,
                    "/web_studio/edit_view": (route, args) => {
                        assert.strictEqual(args.operations[0].type, "add");
                        assert.strictEqual(args.operations[0].position, "before");
                        assert.deepEqual(args.operations[0].target, {
                            tag: "button",
                            attrs: {
                                name: "action_1",
                            },
                            xpath_info: [
                                {
                                    tag: "tree",
                                    indice: 1,
                                },
                                {
                                    tag: "button",
                                    indice: 1,
                                },
                            ],
                        });
                        return createMockViewResult(serverData, "list", arch, "coucou");
                    },
                },
            });

            await dragAndDrop(
                ".o_web_studio_new_fields .o_web_studio_field_char",
                ".o_web_studio_hook",
                "top"
            );
        });

        QUnit.test("new field after a button_group", async function (assert) {
            assert.expect(3);

            const arch = `<tree>
                <field name='display_name'/>
                <button name="action_1" type="object"/>
                <button name="action_2" type="object"/>
            </tree>`;

            await createViewEditor({
                serverData,
                type: "list",
                resModel: "coucou",
                arch,
                mockRPC: {
                    ...defaultMockRpc,
                    "/web_studio/edit_view": (route, args) => {
                        assert.strictEqual(args.operations[0].type, "add");
                        assert.strictEqual(args.operations[0].position, "after");
                        assert.deepEqual(args.operations[0].target, {
                            tag: "button",
                            attrs: {
                                name: "action_2",
                            },
                            xpath_info: [
                                {
                                    tag: "tree",
                                    indice: 1,
                                },
                                {
                                    tag: "button",
                                    indice: 2,
                                },
                            ],
                        });
                        return createMockViewResult(serverData, "list", arch, "coucou");
                    },
                },
            });

            await dragAndDrop(
                ".o_web_studio_new_fields .o_web_studio_field_char",
                ".o_web_studio_hook:nth-child(5)",
                "top"
            );
        });

        QUnit.test("prevent click on button", async (assert) => {
            const fakeActionService = {
                start() {
                    return {
                        doAction() {
                            assert.step("doAction");
                        },
                        doActionButton() {
                            assert.step("doActionButton");
                        },
                    };
                },
            };

            registry.category("services").add("action", fakeActionService, { force: true });

            await createViewEditor({
                serverData,
                resModel: "coucou",
                type: "list",
                arch: `
                    <tree>
                        <field name='display_name'/>
                        <button name="action_1" type="object"/>
                    </tree>
                `,
                mockRPC: defaultMockRpc,
            });

            await click(target.querySelector(".o_data_cell button"));
            assert.verifySteps([]);
        });

        QUnit.test("invisible field in list editor", async function (assert) {
            assert.expect(3);

            const arch = '<tree><field invisible="1" name="display_name"/></tree>';

            await createViewEditor({
                serverData,
                resModel: "coucou",
                type: "list",
                arch: arch,
                mockRPC: defaultMockRpc,
            });

            await showViewTab();
            await click(target, "#show_invisible");
            assert.containsN(target, "td[name='display_name'].o_web_studio_show_invisible", 2);

            await click(
                target,
                "tr:first-child td[name='display_name'].o_web_studio_show_invisible"
            );
            assert.containsOnce(target, "#invisible");

            assert.ok(target.querySelector("#invisible").checked);
        });

        QUnit.test("column invisible field in list editor", async function (assert) {
            assert.expect(3);

            const arch = '<tree><field column_invisible="1" name="display_name"/></tree>';

            await createViewEditor({
                serverData,
                resModel: "coucou",
                type: "list",
                arch: arch,
                mockRPC: defaultMockRpc,
            });

            await showViewTab();
            await click(target, "#show_invisible");
            assert.containsOnce(target, "th[data-name='display_name'].o_web_studio_show_invisible");

            await click(target, "th[data-name='display_name'].o_web_studio_show_invisible");
            assert.containsOnce(target, "#invisible");

            assert.ok(target.querySelector("#invisible").checked);
        });

        QUnit.test("invisible toggle field in list editor", async function (assert) {
            assert.expect(2);
            const changeArch = makeArchChanger();
            const operations = [
                {
                    type: "attributes",
                    target: {
                        tag: "field",
                        attrs: {
                            name: "display_name",
                        },
                        xpath_info: [
                            {
                                tag: "tree",
                                indice: 1,
                            },
                            {
                                tag: "field",
                                indice: 1,
                            },
                        ],
                    },
                    position: "attributes",
                    new_attrs: {
                        column_invisible: "False",
                        invisible: "False",
                    },
                },
            ];

            const archReturn = '<tree><field name="display_name" /></tree>';

            await createViewEditor({
                serverData,
                arch: '<tree><field column_invisible="1" name="display_name"/></tree>',
                resModel: "coucou",
                type: "list",
                mockRPC: {
                    "/web_studio/edit_view": (route, args) => {
                        assert.deepEqual(args.operations, operations);
                        changeArch(args.view_id, archReturn);
                    },
                },
            });

            await showViewTab();
            await click(target, "#show_invisible");
            await click(target, "th[data-name='display_name'].o_web_studio_show_invisible");
            await click(target, "#invisible");
            await nextTick();

            assert.strictEqual(target.querySelector("#invisible").checked, false);
        });

        QUnit.test(
            "field widgets correctly displayed and whitelisted in the sidebar (debug=false)",
            async function (assert) {
                patchWithCleanup(odoo, { debug: false });

                const wowlFieldRegistry = registry.category("fields");
                const charField = wowlFieldRegistry.get("char");
                // Clean registry to avoid having noise from all the other widgets
                wowlFieldRegistry.getEntries().forEach(([key]) => {
                    wowlFieldRegistry.remove(key);
                });

                class SafeWidget extends charField.component {}
                wowlFieldRegistry.add("safeWidget", {
                    ...charField,
                    component: SafeWidget,
                    displayName: "Test Widget",
                });
                setFieldAvailableInSidebar("safeWidget");

                class safeWidgetNoDisplayName extends charField.component {}
                wowlFieldRegistry.add("safeWidgetNoDisplayName", {
                    ...charField,
                    component: safeWidgetNoDisplayName,
                    displayName: null,
                });
                setFieldAvailableInSidebar("safeWidgetNoDisplayName");

                class UnsafeWidget extends charField.component {}
                wowlFieldRegistry.add("unsafeWidget", {
                    ...charField,
                    component: UnsafeWidget,
                });

                await createViewEditor({
                    serverData,
                    type: "list",
                    resModel: "coucou",
                    arch: "<tree><field name='display_name'/></tree>",
                });

                await click(target, "thead th[data-studio-xpath]");
                await click(target, ".o_web_studio_property_widget .o_select_menu_toggler");
                assert.deepEqual(
                    Array.from(
                        target.querySelectorAll(
                            ".o_web_studio_property_widget .o_select_menu_item_label"
                        )
                    ).map((el) => el.textContent.trim()),
                    ["(safeWidgetNoDisplayName)", "Test Widget (safeWidget)"]
                );
            }
        );

        QUnit.test(
            "field widgets correctly displayed and whitelisted in the sidebar (debug=true)",
            async function (assert) {
                patchWithCleanup(odoo, { debug: true });

                const wowlFieldRegistry = registry.category("fields");
                const charField = wowlFieldRegistry.get("char");
                // Clean registry to avoid having noise from all the other widgets
                wowlFieldRegistry.getEntries().forEach(([key]) => {
                    wowlFieldRegistry.remove(key);
                });

                class SafeWidget extends charField.component {}
                wowlFieldRegistry.add("safeWidget", {
                    ...charField,
                    component: SafeWidget,
                    displayName: "Test Widget",
                });
                setFieldAvailableInSidebar("safeWidget");

                class safeWidgetNoDisplayName extends charField.component {}
                wowlFieldRegistry.add("safeWidgetNoDisplayName", {
                    ...charField,
                    component: safeWidgetNoDisplayName,
                    displayName: null,
                });
                setFieldAvailableInSidebar("safeWidgetNoDisplayName");

                class UnsafeWidget extends charField.component {}
                wowlFieldRegistry.add("unsafeWidget", {
                    ...charField,
                    component: UnsafeWidget,
                });

                await createViewEditor({
                    serverData,
                    type: "list",
                    resModel: "coucou",
                    arch: "<tree><field name='display_name'/></tree>",
                });

                await click(target, "thead th[data-studio-xpath]");
                await click(target, ".o_web_studio_property_widget .o_select_menu_toggler");
                assert.deepEqual(
                    Array.from(
                        target.querySelectorAll(
                            ".o_web_studio_property_widget .o_select_menu_item_label"
                        )
                    ).map((el) => el.textContent.trim()),
                    ["(safeWidgetNoDisplayName)", "Test Widget (safeWidget)", "Text (unsafeWidget)"]
                );
            }
        );

        QUnit.test("visible studio hooks in listview", async function (assert) {
            assert.expect(2);
            const changeArch = makeArchChanger();
            await createViewEditor({
                serverData,
                type: "list",
                resModel: "coucou",
                arch: '<tree><field name="display_name"/></tree>',
                async mockRPC(route, args) {
                    if (route === "/web_studio/edit_view") {
                        const arch = `
                            <tree editable='bottom'>
                                <field name='display_name'/>
                            </tree>`;
                        changeArch(args.view_id, arch);
                    }
                    if (route === "/web/dataset/call_kw/coucou/web_search_read") {
                        return {
                            records: [],
                            length: 0,
                        };
                    }
                },
            });

            assert.ok(
                target.querySelector("th.o_web_studio_hook").offsetWidth,
                "studio hooks should be visible in non-editable listview"
            );

            // check the same with editable list 'bottom'
            await click(target.querySelector(".nav-tabs > li:nth-child(2) a"));
            await editAnySelect(
                target,
                ".o_web_studio_sidebar .o_web_studio_property_editable .o_select_menu",
                "Add record at the bottom"
            );
            assert.ok(
                target.querySelector("th.o_web_studio_hook").offsetWidth,
                "studio hooks should be visible in editable 'bottom' listview"
            );
        });

        QUnit.test("sortby and orderby field in sidebar", async function (assert) {
            assert.expect(7);
            const changeArch = makeArchChanger();

            let editViewCount = 0;
            serverData.models.coucou.fields.display_name.store = true;
            serverData.models.coucou.fields.char_field.store = true;

            const arch = `
                <tree default_order='char_field desc, display_name asc'>
                    <field name='display_name'/>
                    <field name='char_field'/>
                </tree>`;

            await createViewEditor({
                serverData,
                type: "list",
                resModel: "coucou",
                arch: arch,
                mockRPC(route, args) {
                    if (route === "/web/dataset/call_kw/coucou/web_search_read") {
                        return {
                            records: [],
                            length: 0,
                        };
                    }
                    if (route === "/web_studio/edit_view") {
                        editViewCount++;
                        let newArch = arch;
                        if (editViewCount === 1) {
                            newArch = `
                                <tree default_order='display_name asc'>
                                    <field name='display_name'/>
                                    <field name='char_field'/>
                                </tree>`;
                        } else if (editViewCount === 2) {
                            newArch = `
                                <tree default_order='display_name desc'>
                                    <field name='display_name'/>
                                    <field name='char_field'/>
                                </tree>`;
                        } else if (editViewCount === 3) {
                            newArch = `
                                <tree>
                                    <field name='display_name'/>
                                    <field name='char_field'/>
                                </tree>`;
                        }
                        changeArch(args.view_id, newArch);
                    }
                },
            });

            await click(target.querySelector(".nav-tabs > li:nth-child(2) a"));
            assert.containsOnce(
                target,
                ".o_web_studio_property_sort_by .o_select_menu",
                "Sortby select box should be exist in slidebar."
            );

            assert.strictEqual(
                target
                    .querySelector(".o_web_studio_property_sort_by .o_select_menu .text-start")
                    .innerText.toUpperCase(),
                "A CHAR",
                "First field should be selected from multiple fields when multiple sorting fields applied on view."
            );

            assert.strictEqual(
                target
                    .querySelector(".o_web_studio_property_sort_order .o_select_menu .text-start")
                    .innerText.toUpperCase(),
                "DESCENDING",
                "Default order mustbe as per first field selected."
            );

            await editAnySelect(target, ".o_web_studio_property_sort_by .o_select_menu", "Name");

            assert.strictEqual(
                target
                    .querySelector(".o_web_studio_property_sort_order .o_select_menu .text-start")
                    .innerText.toUpperCase(),
                "ASCENDING",
                "Default order should be in ascending order"
            );

            assert.containsOnce(
                target,
                ".o_web_studio_property_sort_order",
                "Orderby field must be visible."
            );

            await editAnySelect(
                target,
                ".o_web_studio_property_sort_order .o_select_menu",
                "Descending"
            );

            assert.strictEqual(
                target
                    .querySelector(".o_web_studio_property_sort_order .o_select_menu .text-start")
                    .innerText.toUpperCase(),
                "DESCENDING",
                "Default order should be in ascending order"
            );

            await click(target, ".o_web_studio_property_sort_by .o_select_menu_toggler_clear");

            assert.containsNone(
                target,
                ".o_web_studio_property_sort_order",
                "Orderby field must not be visible."
            );
        });

        QUnit.test("many2many, one2many and binary fields cannot be selected in SortBy dropdown for list editor", async function (assert) {
            assert.expect(4);

            serverData.models.coucou.fields.m2m_field = {
                string: "Many2Many Field",
                type: "many2many",
                relation: "product",
            };

            serverData.models.coucou.fields.binary_field = {
                string: "Binary Field",
                type: "binary",
            };

            await createViewEditor({
                serverData,
                type: "list",
                resModel: "coucou",
                arch: `
                    <tree>
                        <field name="id"/>
                        <field name="display_name"/>
                        <field name="m2o"/>
                        <field name="product_ids"/>
                        <field name="m2m_field"/>
                        <field name="binary_field"/>
                    </tree>
                `,
            });

            await click(target.querySelector(".nav-tabs > li:nth-child(2) a"));

            // Check that the one2many, many2many and binary fields are present in the view
            assert.containsOnce(target, 'th[data-studio-xpath="/tree[1]/field[4]"]', "One2many field is present in the view");
            assert.containsOnce(target, 'th[data-studio-xpath="/tree[1]/field[5]"]', "Many2many field is present in the view");
            assert.containsOnce(target, 'th[data-studio-xpath="/tree[1]/field[6]"]', "Binary field is present in the view");

            // Check that the one2many, many2many and binary fields cannot be selected in the Sort By dropdown
            await click(target.querySelector(".o_web_studio_sidebar .o_web_studio_property_sort_by .o_select_menu_toggler"));
            const sortByDropdownMenu = target.querySelectorAll(".dropdown-item.o_select_menu_item");
            assert.strictEqual(sortByDropdownMenu.length, 3, "There should be 3 items in the Sort By dropdown");
        });

        QUnit.test(
            "already selected unsafe widget without description property should be shown in sidebar with its technical name",
            async function (assert) {
                assert.expect(1);

                const wowlFieldRegistry = registry.category("fields");
                const charField = wowlFieldRegistry.get("char");
                class widgetWithoutDescription extends charField.component {}
                wowlFieldRegistry.add("widgetWithoutDescription", {
                    ...charField,
                    component: widgetWithoutDescription,
                    displayName: null,
                });

                await createViewEditor({
                    serverData,
                    type: "list",
                    resModel: "coucou",
                    arch: "<tree><field name='display_name' widget='widgetWithoutDescription'/></tree>",
                    mockRPC: (route, args) => {
                        if (route === "/web/dataset/call_kw/res.users/has_group") {
                            return true;
                        }
                        if (route === "/web/dataset/call_kw/coucou/web_search_read") {
                            return {
                                records: [],
                                length: 0,
                            };
                        }
                    },
                });

                await click(target.querySelector("thead th[data-studio-xpath]"));
                assert.strictEqual(
                    target
                        .querySelector(".o_web_studio_property_widget .text-start")
                        .innerText.toUpperCase(),
                    "(WIDGETWITHOUTDESCRIPTION)",
                    "widget without description should be there with technical name"
                );
            }
        );

        QUnit.test(
            "already selected widget wihtout supportingTypes should be shown in sidebar with its technical name",
            async function (assert) {
                assert.expect(1);

                const wowlFieldRegistry = registry.category("fields");
                const charField = wowlFieldRegistry.get("char");
                class widgetWithoutTypes extends charField.component {}
                wowlFieldRegistry.add("widgetWithoutTypes", {
                    ...charField,
                    component: widgetWithoutTypes,
                    supportedTypes: null,
                    displayName: null,
                });

                await createViewEditor({
                    serverData,
                    type: "list",
                    resModel: "coucou",
                    arch: "<tree><field name='display_name' widget='widgetWithoutTypes'/></tree>",
                    mockRPC: (route, args) => {
                        if (route === "/web/dataset/call_kw/res.users/has_group") {
                            return true;
                        }
                        if (route === "/web/dataset/call_kw/coucou/web_search_read") {
                            return {
                                records: [],
                                length: 0,
                            };
                        }
                    },
                });

                await click(target.querySelector("thead th[data-studio-xpath]"));
                assert.strictEqual(
                    target
                        .querySelector(".o_web_studio_property_widget .text-start")
                        .innerText.toUpperCase(),
                    "(WIDGETWITHOUTTYPES)",
                    "widget without description should be there with technical name"
                );
            }
        );

        QUnit.test(
            "already selected unsafe widget without description property should be shown in sidebar with its technical name",
            async function (assert) {
                assert.expect(2);

                patchWithCleanup(odoo, { debug: false });

                const wowlFieldRegistry = registry.category("fields");
                const charField = wowlFieldRegistry.get("char");
                class widgetWithoutDescription extends charField.component {}
                wowlFieldRegistry.add("widgetWithoutDescription", {
                    ...charField,
                    component: widgetWithoutDescription,
                    displayName: null,
                });

                await createViewEditor({
                    serverData,
                    resModel: "coucou",
                    type: "list",
                    arch: "<tree><field name='display_name' widget='widgetWithoutDescription'/></tree>",
                });

                await click(target.querySelector("thead th[data-studio-xpath]"));
                assert.containsOnce(
                    target,
                    ".o_web_studio_property_widget",
                    "widget without description should be there"
                );
                assert.strictEqual(
                    target.querySelector(
                        ".o_web_studio_property_widget .o_select_menu_toggler_slot"
                    ).innerText,
                    "(widgetWithoutDescription)",
                    "Widget should have technical name i.e. widgetWithoutDescription as it does not have description"
                );
            }
        );

        QUnit.test(
            "already selected widget without supportingTypes should be shown in sidebar with its technical name",
            async function (assert) {
                assert.expect(2);

                patchWithCleanup(odoo, { debug: false });

                const wowlFieldRegistry = registry.category("fields");
                const charField = wowlFieldRegistry.get("char");
                class widgetWithoutTypes extends charField.component {}
                wowlFieldRegistry.add("widgetWithoutTypes", {
                    ...charField,
                    component: widgetWithoutTypes,
                    supportedTypes: null,
                    displayName: null,
                });

                await createViewEditor({
                    serverData,
                    resModel: "coucou",
                    type: "list",
                    arch: "<tree><field name='display_name' widget='widgetWithoutTypes'/></tree>",
                });

                await click(target.querySelector("thead th[data-studio-xpath]"));
                assert.containsOnce(
                    target,
                    ".o_web_studio_property_widget",
                    "widget without description should be there"
                );
                assert.strictEqual(
                    target.querySelector(
                        ".o_web_studio_property_widget .o_select_menu_toggler_slot"
                    ).innerText,
                    "(widgetWithoutTypes)",
                    "Widget should have technical name i.e. widgetWithoutDescription as it does not have description"
                );
            }
        );

        QUnit.test("editing selection field of list of form view", async function (assert) {
            assert.expect(3);

            const arch = `
                <form>
                    <group>
                        <field name="product_ids"><tree>
                            <field name="toughness"/>
                        </tree></field>
                    </group>
                </form>`;
            await createViewEditor({
                serverData,
                type: "form",
                resModel: "coucou",
                arch: arch,
                mockRPC(route, args) {
                    if (route === "/web_studio/edit_field") {
                        assert.strictEqual(args.model_name, "product");
                        assert.strictEqual(args.field_name, "toughness");
                        assert.deepEqual(args.values, {
                            selection: '[["0","Hard"],["1","Harder"],["Hardest","Hardest"]]',
                        });
                        return Promise.resolve({});
                    }
                    if (route === "/web_studio/edit_view") {
                        return Promise.resolve({});
                    }
                    if (route === "/web_studio/get_default_value") {
                        return Promise.resolve({});
                    }
                    if (route === "/web/dataset/call_kw/res.users/has_group") {
                        return true;
                    }
                    if (route === "/web/dataset/call_kw/coucou/web_search_read") {
                        return {
                            records: [],
                            length: 0,
                        };
                    }
                },
            });

            // open list view
            await click(target.querySelector(".o_field_one2many"));
            await click(target.querySelector('button.o_web_studio_editX2Many[data-type="list"]'));
            await nextTick();

            // add value to "toughness" selection field
            await click(target.querySelector("th[data-studio-xpath]"));
            await click(target.querySelector(".o_web_studio_edit_selection_values"));
            await editInput(target, ".o-web-studio-interactive-list-item-input", "Hardest");
            await click(target.querySelector(".o_web_studio_add_selection button"));
            await click(target.querySelector(".modal .btn-primary"));
        });

        QUnit.test(
            "deleting selection field value which is linked in other records",
            async function (assert) {
                assert.expect(8);

                let editCalls = 0;

                await createViewEditor({
                    serverData,
                    type: "form",
                    resModel: "coucou",
                    arch: `<form>
                        <group>
                            <field name="priority"/>
                        </group>
                    </form>`,
                    mockRPC: function (route, args) {
                        if (route === "/web_studio/edit_field") {
                            editCalls++;
                            if (editCalls === 1) {
                                // High selection value removed
                                assert.deepEqual(args.values, {
                                    selection: '[["1","Low"],["2","Medium"]]',
                                });
                                assert.notOk(args.force_edit, "force_edit is false");
                                return Promise.resolve({
                                    records_linked: 3,
                                    message:
                                        "There are 3 records linked, upon confirming records will be deleted.",
                                });
                            } else if (editCalls === 2) {
                                assert.deepEqual(args.values, {
                                    selection: '[["1","Low"],["2","Medium"]]',
                                });
                                assert.ok(args.force_edit, "force_edit is true");
                            }
                            return Promise.resolve({});
                        }
                        if (route === "/web_studio/edit_view") {
                            return Promise.resolve({});
                        }
                        if (route === "/web/dataset/call_kw/res.users/has_group") {
                            return true;
                        }
                        if (route === "/web/dataset/call_kw/coucou/web_search_read") {
                            return {
                                records: [],
                                length: 0,
                            };
                        }
                    },
                });

                await click(target.querySelector(".o_form_label"));
                await click(target.querySelector(".o_web_studio_edit_selection_values"));
                assert.containsN(
                    target.querySelector(".modal"),
                    ".o_web_studio_selection_editor > li",
                    3,
                    "there should be 3 selection values"
                );

                await click(
                    target.querySelector(
                        ".o_web_studio_selection_editor > li:nth-child(3) .fa-trash-o"
                    )
                );
                assert.containsN(
                    target.querySelector(".modal"),
                    ".o_web_studio_selection_editor > li",
                    2,
                    "there should be 2 selection values"
                );

                await click(target.querySelector(".modal .btn-primary"));
                assert.containsN(target, ".modal", 2, "should contain 2 modals");
                assert.strictEqual(
                    target.querySelector(".o_dialog:not(.o_inactive_modal) .modal-body")
                        .textContent,
                    "There are 3 records linked, upon confirming records will be deleted.",
                    "should have right message"
                );

                await click(target.querySelector(".o_dialog:not(.o_inactive_modal) .btn-primary"));
            }
        );

        QUnit.test("add a selection field in non debug", async function (assert) {
            assert.expect(9);

            // Inline edition of selection values is only available in non debug mode
            patchWithCleanup(odoo, { debug: false });
            const arch = "<tree><field name='display_name'/></tree>";
            await createViewEditor({
                serverData,
                type: "list",
                resModel: "coucou",
                arch: arch,
                mockRPC(route, args) {
                    if (route === "/web_studio/edit_view") {
                        assert.strictEqual(
                            args.operations[0].node.field_description.selection,
                            '[["Value 1","Miramar"]]',
                            "the selection value should be set correctly"
                        );
                        return createMockViewResult(serverData, "list", arch, "coucou");
                    }
                },
            });

            await dragAndDrop(
                ".o_web_studio_new_fields .o_web_studio_field_selection",
                ".o_web_studio_hook",
                "top"
            );
            assert.containsOnce(
                target,
                ".modal-content.o_web_studio_selection_editor",
                "there should be a selection editor"
            );
            assert.containsNone(
                target,
                ".modal .o_web_studio_selection_editor > li",
                "there should be 0 selection value"
            );
            assert.hasClass(
                target.querySelector(".modal .btn-primary"),
                "disabled",
                "selection with no values cannot be saved"
            );

            // add a new value (with ENTER)
            await editInput(target, ".modal .o_web_studio_add_selection input", "Value 1");
            await triggerEvent(target, ".modal .o_web_studio_add_selection input", "keypress", {
                key: "Enter",
            });
            assert.containsOnce(
                target,
                ".modal .o_web_studio_selection_editor > li",
                "there should be 1 selection value"
            );
            assert.containsOnce(
                target,
                ".modal .o_web_studio_selection_editor > li span:contains(Value 1)",
                "the value should be correctly set"
            );

            // edit the first value
            await click(target.querySelector(".modal li .o-web-studio-interactive-list-edit-item"));
            assert.containsOnce(
                target,
                ".modal .o_web_studio_selection_editor > li input",
                "the line is now editable with an input"
            );
            assert.strictEqual(
                target.querySelector(".modal .o_web_studio_selection_editor li input").value,
                "Value 1",
                "the value should be set in the input in li"
            );

            await editInput(
                target,
                ".modal .o_web_studio_selection_editor ul:first-child input",
                "Miramar"
            );
            await click(
                target.querySelector(
                    ".modal .o_web_studio_selection_editor ul:first-child button.fa-check"
                )
            );
            assert.strictEqual(
                target.querySelector(".modal .o_web_studio_selection_editor ul:first-child li")
                    .textContent,
                "Miramar",
                "the value should have been updated"
            );

            // Click 'Confirm' button for the new field dialog
            await click(target.querySelector(".modal .btn-primary"));
        });

        QUnit.test("add a selection field in debug", async function (assert) {
            assert.expect(15);

            // Advanced edition of selection values is only available in debug mode
            patchWithCleanup(odoo, { debug: true });
            const arch = "<tree><field name='display_name'/></tree>";
            await createViewEditor({
                serverData,
                type: "list",
                resModel: "coucou",
                arch: arch,
                mockRPC(route, args) {
                    if (route === "/web_studio/edit_view") {
                        assert.strictEqual(
                            args.operations[0].node.field_description.selection,
                            '[["Value 2","Value 2"],["Value 1","My Value"],["Sulochan","Sulochan"]]',
                            "the selection should be set"
                        );
                        assert.ok(true, "should have refreshed the view");
                        return createMockViewResult(serverData, "list", arch, "coucou");
                    }
                },
            });

            await dragAndDrop(
                ".o_web_studio_new_fields .o_web_studio_field_selection",
                ".o_web_studio_hook",
                "top"
            );
            assert.containsOnce(
                target,
                ".modal-content.o_web_studio_selection_editor",
                "there should be a selection editor"
            );
            assert.containsNone(
                target,
                ".modal .o_web_studio_selection_editor > li",
                "there should be 0 selection value"
            );
            assert.hasClass(
                target.querySelector(".modal .btn-primary"),
                "disabled",
                "selection with no values cannot be saved"
            );

            // add a new value (with ENTER)
            await editInput(target, ".modal .o_web_studio_add_selection input", "Value 1");
            await triggerEvent(target, ".modal .o_web_studio_add_selection input", "keypress", {
                key: "Enter",
            });
            assert.containsOnce(
                target,
                ".modal .o_web_studio_selection_editor > li",
                "there should be 1 selection value"
            );
            assert.containsOnce(
                target,
                ".modal .o_web_studio_selection_editor > li span:contains(Value 1)",
                "the value should be correctly set"
            );

            // add a new value (with button 'fa-check' )
            await editInput(target, ".modal .o-web-studio-interactive-list-item-input", "Value 2");
            await click(
                target.querySelector(
                    ".modal .o_web_studio_selection_editor ul:nth-child(2) button.fa-check"
                )
            );
            assert.containsN(
                target,
                ".modal .o_web_studio_selection_editor > li",
                2,
                "there should be 2 selection values"
            );

            // edit the first value
            await click(
                target.querySelector(
                    ".modal .o_web_studio_selection_editor ul:first-child .o-web-studio-interactive-list-edit-item"
                )
            );

            assert.containsOnce(
                target,
                ".modal .o_web_studio_selection_full_edit",
                "a new UI is visible for an advanced edition"
            );
            assert.strictEqual(
                target.querySelector(".o_web_studio_selection_full_edit label:nth-child(2) input")
                    .value,
                "Value 1",
                "the value should be set in the edition modal"
            );
            await editInput(
                target,
                ".o_web_studio_selection_full_edit label:nth-child(2) input",
                "My Value"
            );
            await click(target.querySelector(".o_web_studio_selection_full_edit .fa-check"));
            assert.containsNone(
                target,
                ".o_web_studio_selection_full_edit",
                "the advanced edition UI is no longer visible"
            );
            assert.strictEqual(
                target.querySelector(".modal .o_web_studio_selection_editor ul li:first-child")
                    .textContent,
                "My Value",
                "the value should have been updated"
            );

            // add a value and delete it
            await editInput(target, ".modal .o-web-studio-interactive-list-item-input", "Value 3");
            await click(
                target.querySelector(
                    ".modal .o_web_studio_selection_editor ul:nth-child(2) button.fa-check"
                )
            );
            assert.containsN(
                target,
                ".modal .o_web_studio_selection_editor > li",
                3,
                "there should be 3 selection values"
            );

            await click(
                target.querySelector(
                    ".modal .o_web_studio_selection_editor > li:nth-child(3) .fa-trash-o"
                )
            );
            assert.containsN(
                target,
                ".modal .o_web_studio_selection_editor > li",
                2,
                "there should be 2 selection values"
            );

            // reorder values
            await dragAndDrop(
                ".modal .o_web_studio_selection_editor > li:nth-child(2) .o-draggable-handle",
                ".modal .o_web_studio_selection_editor > li:first-child",
                "top"
            );
            assert.strictEqual(
                target.querySelector(".modal .o_web_studio_selection_editor ul li:first-child")
                    .textContent,
                "Value 2",
                "the values should have been reordered"
            );

            // Verify that on confirm, new value is added without button 'fa-check' or 'ENTER'
            await editInput(target, ".modal .o-web-studio-interactive-list-item-input", "Sulochan");
            await click(target.querySelector(".modal .btn-primary"));
        });

        QUnit.test("add a selection field with widget priority", async function (assert) {
            assert.expect(5);

            const arch = "<tree><field name='display_name'/></tree>";
            await createViewEditor({
                serverData,
                type: "list",
                resModel: "coucou",
                arch: arch,
                mockRPC(route, args) {
                    if (route === "/web_studio/edit_view") {
                        assert.strictEqual(
                            args.operations[0].node.field_description.type,
                            "selection",
                            "the type should be correctly set"
                        );
                        assert.deepEqual(
                            args.operations[0].node.field_description.selection,
                            [
                                ["0", "Normal"],
                                ["1", "Low"],
                                ["2", "High"],
                                ["3", "Very High"],
                            ],
                            "the selection should be correctly set"
                        );
                        assert.strictEqual(
                            args.operations[0].node.attrs.widget,
                            "priority",
                            "the widget should be correctly set"
                        );
                        return createMockViewResult(serverData, "list", arch, "coucou");
                    }
                },
            });

            assert.containsOnce(
                target,
                ".o_web_studio_list_view_editor table thead [data-studio-xpath]",
                "there should be one head node"
            );

            // add a priority field
            await dragAndDrop(
                ".o_web_studio_new_fields .o_web_studio_field_priority",
                ".o_web_studio_hook",
                "top"
            );
            assert.containsNone(target, ".modal", "there should be no modal");
        });

        QUnit.test("invisible list editor", async function (assert) {
            assert.expect(4);

            await createViewEditor({
                serverData,
                type: "list",
                resModel: "coucou",
                arch: "<tree><field name='display_name' column_invisible='1'/></tree>",
            });

            assert.containsNone(
                target,
                ".o_list_view [data-studio-xpath]",
                "there should be no node"
            );
            assert.containsOnce(
                target,
                "table thead th.o_web_studio_hook",
                "there should be one hook"
            );

            // click on show invisible
            await showViewTab();
            await click(target, ".o_web_studio_sidebar input#show_invisible");

            assert.ok(
                target.querySelectorAll(".o_list_view [data-studio-xpath]").length > 0,
                "there should be multiple visible nodes"
            );
            assert.containsN(
                target,
                "table thead th.o_web_studio_hook",
                2,
                "there should be two hooks (before & after the field)"
            );
        });

        QUnit.test("list editor with header and invisible element", async function (assert) {
            assert.expect(4);

            await createViewEditor({
                serverData,
                type: "list",
                resModel: "coucou",
                arch: `
                    <tree string='List'>
                        <header>
                            <button name="action_do_something" type="object" string="The Button"/>
                        </header>
                        <field name='name' class="my_super_name_class" />
                        <field name='char_field' class="my_super_description_class" invisible="True"/>
                    </tree>
                `,
            });

            assert.isVisible(
                target.querySelector("td.my_super_name_class"),
                "The name field should be visible"
            );
            assert.containsNone(
                target,
                "my_super_description_class",
                "The description field should not exist"
            );

            // click on show invisible
            await showViewTab();
            await click(target, ".o_web_studio_sidebar input#show_invisible");

            assert.isVisible(
                target.querySelector("td.my_super_name_class"),
                "The name field should still be visible"
            );
            assert.isVisible(
                target.querySelector("td.my_super_description_class"),
                "The description field should be visible"
            );
        });

        QUnit.test("show invisible state is kept between sidebar panels", async function (assert) {
            await createViewEditor({
                serverData,
                type: "list",
                resModel: "coucou",
                arch: `<tree string='List'>
                        <field name='name' class="my_super_name_class" />
                        <field name='char_field' class="my_super_description_class" invisible="True"/>
                    </tree>`,
            });

            await showViewTab();
            assert.notOk(
                document.querySelector("input#show_invisible").checked,
                "show invisible checkbox is not checked"
            );

            await click(document, ".o_web_studio_sidebar input#show_invisible");
            assert.ok(
                document.querySelector("input#show_invisible").checked,
                "show invisible checkbox should be checked"
            );

            await showNewTab();
            await showViewTab();
            assert.ok(
                document.querySelector("input#show_invisible").checked,
                "show invisible checkbox should be checked"
            );
        });

        QUnit.test("list editor with control node tag", async function (assert) {
            assert.expect(2);

            await createViewEditor({
                serverData,
                type: "list",
                resModel: "coucou",
                arch: "<tree><control><create string='Add a line'/></control></tree>",
            });

            assert.containsNone(
                target,
                ".o_list_view [data-studio-xpath]",
                "there should be no node"
            );

            // click on show invisible
            await showViewTab();
            await click(target, ".o_web_studio_sidebar input#show_invisible");

            assert.containsNone(
                target,
                ".o_list_view [data-studio-xpath]",
                "there should be no nodes (the control is filtered)"
            );
        });

        QUnit.test("list editor invisible to visible on field", async function (assert) {
            patchWithCleanup(session, {
                user_context: {
                    lang: "fr_FR",
                    tz: "Europe/Brussels",
                },
            });

            const changeArch = makeArchChanger();
            const archReturn = `<tree><field name='display_name'/><field name="char_field" /></tree>`;

            await createViewEditor({
                type: "list",
                serverData,
                resModel: "coucou",
                arch: `<tree><field name='display_name'/>
                    <field name='char_field' column_invisible='1'/>
                </tree>`,
                mockRPC: function (route, args) {
                    if (route === "/web_studio/edit_view") {
                        assert.step("edit_view");
                        assert.strictEqual(
                            args.context.tz,
                            "Europe/Brussels",
                            "The tz from user_context should have been passed"
                        );
                        assert.strictEqual(
                            args.context.lang,
                            false,
                            "The lang in context should be false explicitly"
                        );
                        assert.strictEqual(args.operations[0].new_attrs.invisible, "False");
                        assert.strictEqual(
                            args.operations[0].new_attrs.column_invisible,
                            "False",
                            "Should remove column_invisible attribute"
                        );
                        changeArch(args.view_id, archReturn);
                    }
                },
            });

            await click(selectorContains(target, ".o_web_studio_sidebar .nav-link", "View"));
            await click(target.querySelector(".o_web_studio_sidebar input#show_invisible"));
            // select the second column
            await click(target.querySelector('thead th[data-studio-xpath="/tree[1]/field[2]"]'));
            assert.verifySteps([]);
            // disable invisible
            await click(target.querySelector(".o_web_studio_sidebar input#invisible"));
            assert.verifySteps(["edit_view"]);
        });

        QUnit.test("list editor invisible to visible on field readonly", async function (assert) {
            const archReturn = `<tree>
                <field name='display_name'/>
                <field name="char_field" column_invisible="True" readonly="True" />
            </tree>`;

            const changeArch = makeArchChanger();
            await createViewEditor({
                serverData,
                type: "list",
                resModel: "coucou",
                arch: `<tree>
                    <field name='display_name'/>
                    <field name='char_field' readonly="True"/>
                </tree>`,
                mockRPC: function (route, args) {
                    if (route === "/web_studio/edit_view") {
                        assert.step("edit_view");
                        assert.ok(
                            !("readonly" in args.operations[0].new_attrs),
                            'we shouldn\'t send "readonly"'
                        );
                        assert.equal(
                            args.operations[0].new_attrs.column_invisible,
                            "True",
                            'we should send "column_invisible"'
                        );

                        changeArch(args.view_id, archReturn);
                    }
                },
            });

            await click(selectorContains(target, ".o_web_studio_sidebar .nav-link", "View"));
            await click(target.querySelector(".o_web_studio_sidebar input#show_invisible"));

            // select the second column
            await click(target.querySelector('thead th[data-studio-xpath="/tree[1]/field[2]"]'));
            // disable invisible
            await click(target.querySelector(".o_web_studio_sidebar input#invisible"));
            assert.verifySteps(["edit_view"]);
        });

        QUnit.test("list editor field", async function (assert) {
            await createViewEditor({
                serverData,
                type: "list",
                resModel: "coucou",
                arch: "<tree><field name='display_name'/></tree>",
            });

            // click on the field
            await click(target.querySelector(".o_web_studio_list_view_editor [data-studio-xpath]"));

            assert.hasClass(
                target.querySelector(".o_web_studio_list_view_editor [data-studio-xpath]"),
                "o-web-studio-editor--element-clicked",
                "the column should have the clicked style"
            );

            assert.hasClass(
                selectorContains(target, ".o_web_studio_sidebar .nav-link", "Properties"),
                "active",
                "the Properties tab should now be active"
            );
            assert.containsOnce(
                target,
                ".o_web_studio_sidebar .o_web_studio_property_widget",
                "the sidebar should now display the field properties"
            );
            assert.strictEqual(
                target.querySelector(`.o_web_studio_sidebar input[name="string"]`).value,
                "Name",
                "the label in sidebar should be Name"
            );
            assert.strictEqual(
                target.querySelector(
                    ".o_web_studio_sidebar .o_web_studio_property_widget .o_select_menu"
                ).textContent,
                "Text (char)",
                "the widget in sidebar should be set by default"
            );
        });

        QUnit.test("add group to field", async function (assert) {
            const changeArch = makeArchChanger();
            serverData.models["res.groups"] = {
                fields: {},
                records: [{ id: 4, display_name: "Admin" }],
            };
            await createViewEditor({
                serverData,
                type: "list",
                resModel: "coucou",
                arch: "<tree><field name='display_name'/></tree>",
                mockRPC: function (route, args) {
                    if (route === "/web_studio/edit_view") {
                        assert.step("edit_view");
                        assert.deepEqual(
                            args.operations[0],
                            {
                                node: {
                                    attrs: { name: "display_name" },
                                    tag: "field",
                                },
                                new_attrs: { groups: [4] },
                                position: "attributes",
                                target: {
                                    attrs: { name: "display_name" },
                                    tag: "field",
                                    xpath_info: [
                                        {
                                            indice: 1,
                                            tag: "tree",
                                        },
                                        {
                                            indice: 1,
                                            tag: "field",
                                        },
                                    ],
                                },
                                type: "attributes",
                            },
                            "the group operation should be correct"
                        );
                        // the server sends the arch in string but it's post-processed
                        // by the ViewEditorManager
                        const arch = `<tree>
                            <field name='display_name' studio_groups='[{&quot;id&quot;:4, &quot;name&quot;: &quot;Admin&quot;}]'/>
                        </tree>`;
                        changeArch(args.view_id, arch);
                    }
                },
            });

            // click on the field
            await click(target.querySelector(".o_web_studio_list_view_editor [data-studio-xpath]"));
            await selectDropdownItem(
                target.querySelector(".o_limit_group_visibility"),
                "groups_id",
                "Admin"
            );
            assert.verifySteps(["edit_view"]);
            assert.containsOnce(
                target,
                ".o_limit_group_visibility .o_field_many2many_tags .badge.o_tag_color_0"
            );
        });

        QUnit.test("sorting rows is disabled in Studio", async function (assert) {
            serverData.models.product.records = [
                {
                    id: 1,
                    display_name: "xpad",
                },
                {
                    id: 2,
                    display_name: "xpod",
                },
            ];

            await createViewEditor({
                serverData,
                type: "list",
                resModel: "product",
                arch: `<tree editable='true'>
                    <field name='id' widget='handle'/>
                    <field name='display_name'/>
                </tree>`,
            });

            assert.containsN(
                target,
                ".ui-sortable-handle",
                2,
                "the widget handle should be displayed"
            );
            assert.strictEqual(
                Array.from(target.querySelectorAll(".o_data_cell"))
                    .map((n) => n.textContent)
                    .join(""),
                "xpadxpod",
                "the records should be ordered"
            );

            await dragAndDrop("tbody tr:nth-child(2) .o_handle_cell", "tbody tr:nth-child(1)");

            assert.strictEqual(
                Array.from(target.querySelectorAll(".o_data_cell"))
                    .map((n) => n.textContent)
                    .join(""),
                "xpadxpod",
                "the records should not have been moved (sortable should be disabled in Studio)"
            );
        });

        QUnit.test("List grouped should not be grouped", async function (assert) {
            serverData.models["coucou"].records = [
                { id: 1, display_name: "Red Right Hand", priority: "1", croissant: 3 },
                { id: 2, display_name: "Hell Broke Luce", priority: "1", croissant: 5 },
            ];

            serverData.views = {
                "coucou,false,list": `<tree><field name='croissant' sum='Total Croissant'/></tree>`,
                "coucou,false,search": `<search><filter string="Priority" name="priority" domain="[]" context="{'group_by':'priority'}"/></search>`,
            };
            registry.category("services").add("enterprise_subscription", {
                start() {
                    return {};
                },
            });
            const webClient = await createEnterpriseWebClient({ serverData });

            await doAction(webClient, {
                type: "ir.actions.act_window",
                res_model: "coucou",
                views: [[false, "list"]],
                context: { search_default_priority: "1" },
                xml_id: "somexmlid",
            });

            assert.containsOnce(
                target,
                ".o_list_view .o_list_table_grouped",
                "The list should be grouped"
            );

            await openStudio(target);

            assert.containsNone(
                target,
                ".o_web_studio_list_view_editor .o_list_table_grouped",
                "The list should not be grouped"
            );
        });

        QUnit.test("move a field in list", async function (assert) {
            const arch = `<tree>
                <field name='display_name'/>
                <field name='char_field'/>
                <field name='m2o'/>
            </tree>`;

            disableHookAnimation(target);
            const changeArch = makeArchChanger();
            await createViewEditor({
                serverData,
                type: "list",
                resModel: "coucou",
                arch,
                mockRPC: function (route, args) {
                    if (route === "/web_studio/edit_view") {
                        assert.step("edit_view");
                        assert.deepEqual(
                            args.operations[0],
                            {
                                node: {
                                    tag: "field",
                                    attrs: { name: "m2o" },
                                    xpath_info: [
                                        {
                                            indice: 1,
                                            tag: "tree",
                                        },
                                        {
                                            indice: 3,
                                            tag: "field",
                                        },
                                    ],
                                },
                                position: "before",
                                target: {
                                    tag: "field",
                                    attrs: { name: "display_name" },
                                    xpath_info: [
                                        {
                                            indice: 1,
                                            tag: "tree",
                                        },
                                        {
                                            indice: 1,
                                            tag: "field",
                                        },
                                    ],
                                },
                                type: "move",
                            },
                            "the move operation should be correct"
                        );
                        // the server sends the arch in string but it's post-processed
                        // by the ViewEditorManager
                        const arch = `<tree>
                            <field name='m2o'/>
                            <field name='display_name'/>
                            <field name='char_field'/>
                        </tree>`;
                        changeArch(args.view_id, arch);
                    }
                },
            });

            assert.strictEqual(
                target.querySelector(".o_web_studio_list_view_editor thead").textContent,
                "NameA charProduct",
                "the columns should be in the correct order"
            );

            // move the m2o at index 0
            await dragAndDrop(
                target.querySelector(
                    '.o_web_studio_list_view_editor th[data-studio-xpath="/tree[1]/field[3]"]'
                ),
                target.querySelector("th.o_web_studio_hook")
            );
            await nextTick();
            assert.verifySteps(["edit_view"]);

            assert.strictEqual(
                target.querySelector(".o_web_studio_list_view_editor thead").textContent,
                "ProductNameA char",
                "the moved field should be the first column"
            );
        });

        QUnit.test("list editor field with aggregate function", async function (assert) {
            const changeArch = makeArchChanger();
            serverData.models.coucou.records = [
                {
                    id: 1,
                    display_name: "Red Right Hand",
                    croissant: 3,
                    float_field: 3.14,
                    money_field: 1.001,
                },
                {
                    id: 2,
                    display_name: "Hell Broke Luce",
                    croissant: 5,
                    float_field: 6.66,
                    money_field: 999.999,
                },
            ];

            const arch =
                '<tree><field name="display_name"/><field name="float_field"/><field name="money_field"/><field name="croissant"/></tree>';
            const sumArchReturn =
                '<tree><field name="display_name"/><field name="float_field"/><field name="money_field"/><field name="croissant" sum="Sum of Croissant"/></tree>';
            const avgArchReturn =
                '<tree><field name="display_name"/><field name="float_field"/><field name="money_field"/><field name="croissant" avg="Average of Croissant"/></tree>';

            await createViewEditor({
                type: "list",
                serverData,
                resModel: "coucou",
                arch,
                mockRPC: function (route, args) {
                    if (route === "/web_studio/edit_view") {
                        assert.step("edit_view");
                        var op = args.operations[args.operations.length - 1];
                        let newArch;
                        if (op.new_attrs.sum !== "") {
                            assert.strictEqual(
                                op.new_attrs.sum,
                                "Sum of Croissant",
                                '"sum" aggregate should be applied'
                            );
                            newArch = sumArchReturn;
                        } else if (op.new_attrs.avg !== "") {
                            assert.strictEqual(
                                op.new_attrs.avg,
                                "Average of Croissant",
                                '"avg" aggregate should be applied'
                            );
                            newArch = avgArchReturn;
                        } else if (op.new_attrs.sum === "" || op.new_attrs.avg == "") {
                            newArch = arch;
                            assert.ok('neither "sum" nor "avg" selected for aggregation');
                        }
                        changeArch(args.view_id, newArch);
                    }
                },
            });

            await click(target.querySelector("thead th[data-studio-xpath]")); // select the first column

            // selecting column other than float, integer or monetary should not show aggregate selection
            assert.containsNone(
                target,
                ".o_web_studio_sidebar o_web_studio_property_aggregate",
                "should not have aggregate selection for character type column"
            );

            await click(target.querySelector('thead th[data-studio-xpath="/tree[1]/field[2]"]')); // select the second column
            assert.containsOnce(
                target,
                ".o_web_studio_sidebar .o_web_studio_property_aggregate",
                "should have aggregate selection for float type column"
            );

            await click(target.querySelector('thead th[data-studio-xpath="/tree[1]/field[3]"]')); // select the third column
            assert.containsOnce(
                target,
                ".o_web_studio_sidebar .o_web_studio_property_aggregate",
                "should have aggregate selection for monetary type column"
            );

            await click(target.querySelector('thead th[data-studio-xpath="/tree[1]/field[4]"]')); // select the fourth column
            assert.containsOnce(
                target,
                ".o_web_studio_sidebar .o_web_studio_property_aggregate",
                "should have aggregate selection for integer type column"
            );

            // select 'sum' aggregate function
            await editAnySelect(
                target,
                ".o_web_studio_sidebar .o_web_studio_property_aggregate .o_select_menu",
                "Sum"
            );
            assert.verifySteps(["edit_view"]);
            assert.strictEqual(
                target.querySelectorAll("tfoot tr td.o_list_number")[1].textContent,
                "8",
                "total should be '8'"
            );
            assert.strictEqual(
                target.querySelectorAll("tfoot tr td.o_list_number span")[1].dataset.tooltip,
                "Sum of Croissant",
                "title should be 'Sum of Croissant'"
            );

            // select 'avg' aggregate function
            await editAnySelect(
                target,
                ".o_web_studio_sidebar .o_web_studio_property_aggregate .o_select_menu",
                "Average"
            );
            assert.verifySteps(["edit_view"]);
            assert.strictEqual(
                target.querySelectorAll("tfoot tr td.o_list_number")[1].textContent,
                "4",
                "total should be '4'"
            );
            assert.strictEqual(
                target.querySelectorAll("tfoot tr td.o_list_number span")[1].dataset.tooltip,
                "Average of Croissant",
                "title should be 'Avg of Croissant'"
            );

            // select '' aggregate function
            await editAnySelect(
                target,
                ".o_web_studio_sidebar .o_web_studio_property_aggregate .o_select_menu",
                "No aggregation"
            );
            assert.verifySteps(["edit_view"]);
            assert.containsOnce(target, "tfoot tr td.o_list_number");
            assert.strictEqual(
                target.querySelector("tfoot tr td.o_list_number").textContent,
                "—",
                "total should display '—'"
            );
            assert.strictEqual(
                target.querySelector("tfoot tr td.o_list_number span").dataset.tooltip,
                "No currency provided",
                "title should be 'No currency provided'"
            );
        });

        QUnit.test("error during tree rendering: undo", async function (assert) {
            serverData.models.coucou.records = [];
            const notificationService = {
                start() {
                    return { add: (message) => assert.step(`notification: ${message}`) };
                },
            };

            registry.category("services").add("notification", notificationService, { force: true });

            let triggerError = false;
            patchWithCleanup(ListRenderer.prototype, {
                setup() {
                    super.setup();
                    onWillRender(() => {
                        if (triggerError) {
                            triggerError = false;
                            throw new Error("Error during rendering");
                        }
                    });
                },
            });

            const errorArch = "<tree />";
            const arch = "<tree><field name='id'/></tree>";

            const changeArch = makeArchChanger();

            await createViewEditor({
                type: "list",
                serverData,
                resModel: "coucou",
                arch,
                mockRPC: (route, args) => {
                    if (route === "/web_studio/edit_view") {
                        assert.step("edit_view");
                        if (triggerError) {
                            changeArch(args.view_id, errorArch);
                        } else {
                            changeArch(args.view_id, arch);
                        }
                    }
                },
            });

            // delete a field to generate a view edition
            await click(target.querySelector(".o_web_studio_list_view_editor [data-studio-xpath]"));
            await click(target.querySelector(".o_web_studio_sidebar .o_web_studio_remove"));
            triggerError = true;
            await click(target.querySelector(".modal .btn-primary"));
            assert.verifySteps([
                "edit_view",
                "notification: The requested change caused an error in the view. It could be because a field was deleted, but still used somewhere else.",
                "edit_view",
            ]);

            assert.containsOnce(target, ".o_web_studio_view_renderer");
            assert.containsOnce(
                target,
                ".o_web_studio_list_view_editor [data-studio-xpath]",
                "the view should be back as normal with 1 field"
            );

            assert.strictEqual(
                target.querySelector(".o_web_studio_sidebar .nav-link.active").textContent,
                "View"
            );
        });

        QUnit.test("error in view edition: undo", async function (assert) {
            /** The list view is taken but really any could have. This tests when the edit_view route fails */
            serverData.models.coucou.records = [];
            const notificationService = {
                start() {
                    return { add: (message) => assert.step(`notification: ${message}`) };
                },
            };
            registry.category("services").add("notification", notificationService, { force: true });
            registry.category("services").add("error", { start() {} });

            const handler = (ev) => {
                assert.strictEqual(ev.reason.message, "Boom");
                assert.step("error");
                ev.preventDefault();
            };
            window.addEventListener("unhandledrejection", handler);
            registerCleanup(() => window.removeEventListener("unhandledrejection", handler));

            let triggerError = true;
            await createViewEditor({
                type: "list",
                serverData,
                resModel: "coucou",
                arch: "<tree><field name='id'/></tree>",
                mockRPC: function (route, args) {
                    if (route === "/web_studio/edit_view") {
                        assert.step("edit_view");
                        if (triggerError) {
                            triggerError = false;
                            // simulate a failed route
                            return Promise.reject(new Error("Boom"));
                        } else {
                            assert.strictEqual(args.operations.length, 1);
                        }
                    }
                },
            });

            assert.containsOnce(
                target,
                ".o_web_studio_list_view_editor [data-studio-xpath]",
                "there should be one field in the view"
            );

            // delete a field to generate a view edition
            await click(target.querySelector(".o_web_studio_list_view_editor [data-studio-xpath]"));
            await click(target.querySelector(".o_web_studio_sidebar .o_web_studio_remove"));
            await click(target.querySelector(".modal-dialog .btn-primary"));
            assert.verifySteps([
                "edit_view",
                "notification: This operation caused an error, probably because a xpath was broken",
                "error",
            ]);

            assert.containsOnce(
                target,
                ".o_web_studio_list_view_editor [data-studio-xpath]",
                "the view should be back as normal with 1 field"
            );
            assert.strictEqual(
                target.querySelector(".o_web_studio_sidebar .nav-link.active").textContent,
                "View"
            );

            await click(target.querySelector(".o_web_studio_list_view_editor [data-studio-xpath]"));
            await click(target.querySelector(".o_web_studio_sidebar .o_web_studio_remove"));
            await click(target.querySelector(".modal-dialog .btn-primary"));
            assert.verifySteps(["edit_view"]);
        });

        QUnit.test("Default group by field in sidebar", async function (assert) {
            const changeArch = makeArchChanger();

            let editViewCount = 0;
            serverData.models.coucou.fields.display_name.store = true;
            serverData.models.coucou.fields.char_field.store = true;

            const arch = `
                <tree>
                    <field name='display_name'/>
                    <field name='char_field'/>
                </tree>`;

            await createViewEditor({
                serverData,
                type: "list",
                resModel: "coucou",
                arch: arch,
                mockRPC(route, args) {
                    if (route === "/web/dataset/call_kw/coucou/web_search_read") {
                        return { records: [], length: 0 };
                    }
                    if (route === "/web_studio/edit_view") {
                        let newArch = arch;
                        editViewCount++;
                        if (editViewCount === 1) {
                            newArch = `
                                <tree default_group_by='display_name'>
                                    <field name='display_name'/>
                                    <field name='char_field'/>
                                </tree>
                            `;
                        }
                        changeArch(args.view_id, newArch);
                    }
                },
            });

            await click(target.querySelector(".nav-tabs > li:nth-child(2) a"));
            assert.containsOnce(
                target,
                ".o_web_studio_property_default_group_by .o_select_menu",
                "Default group by select box should exist in sidebar."
            );

            assert.containsNone(
                target,
                ".o_web_studio_property_default_group_by .o_select_menu_toggler_clear",
                "No value should be set."
            );

            await click(target, ".o_web_studio_property_default_group_by .o_select_menu button");
            const choices = [...target.querySelectorAll(".o_select_menu_item")].map((el) =>
                el.innerText.toUpperCase()
            );

            assert.deepEqual(choices, ["A CHAR", "NAME"]);

            await click(target, ".o_select_menu_item:nth-child(2)");

            assert.strictEqual(
                target
                    .querySelector(
                        ".o_web_studio_property_default_group_by .o_select_menu .text-start"
                    )
                    .innerText.toUpperCase(),
                "NAME",
                "Default group by should be equal to 'Name'."
            );

            assert.containsOnce(
                target,
                ".o_web_studio_property_default_group_by + .alert",
                "There should be an alert stating that a default group by is set but not visible in studio."
            );

            await click(
                target,
                ".o_web_studio_property_default_group_by .o_select_menu_toggler_clear"
            );

            assert.containsNone(
                target,
                ".o_web_studio_property_default_group_by + .alert",
                "The alert should not be visible anymore."
            );
        });

        QUnit.test("click on a link doesn't do anything", async function (assert) {
            serverData.models.coucou.records.push({ display_name: "Red Right Hand", m2o: 1 });

            patchWithCleanup(ListEditorRenderer.prototype, {
                onTableClicked(ev) {
                    assert.step("onTableClicked");
                    assert.ok(!ev.defaultPrevented);
                    super.onTableClicked(ev);
                    assert.ok(ev.defaultPrevented);
                },
            });

            await createViewEditor({
                serverData,
                type: "list",
                resModel: "coucou",
                arch: `<tree><field name="display_name"/><field name="m2o" widget="many2one"/></tree>`,
            });

            await click(target, "[name='m2o'] a");
            assert.verifySteps(["onTableClicked"]);
        });

        QUnit.test("invisible relational are fetched", async (assert) => {
            serverData.models.coucou.fields.product_ids = { type: "one2many", relation: "product" };
            serverData.models.coucou.records = [
                {
                    id: 1,
                    product_ids: [1],
                    m2o: 1,
                },
            ];

            const mockRPC = (route, args) => {
                if (args.method === "web_search_read") {
                    assert.step("web_search_read");
                    assert.deepEqual(args.kwargs.specification, {
                        m2o: { fields: { display_name: {} } },
                        product_ids: { fields: {} },
                    });
                }
            };

            await createViewEditor({
                serverData,
                type: "list",
                resModel: "coucou",
                arch: '<tree><field name="product_ids" invisible="True" /><field name="m2o" invisible="True" /></tree>',
                mockRPC,
            });

            assert.strictEqual(target.querySelector("tbody .o_data_row").innerText.trim(), "");
            await click(selectorContains(target, ".o_web_studio_sidebar .nav-link", "View"));
            await click(target, ".o_web_studio_sidebar #show_invisible");
            assert.strictEqual(
                target.querySelector("tbody .o_data_row").innerText.trim(),
                "1 record\t\tA very good product"
            );
            assert.verifySteps(["web_search_read"]);
        });

        QUnit.test("List readonly attribute should not set force_save", async function (assert) {
            assert.expect(2);
            const changeArch = makeArchChanger();

            const arch = '<tree><field name="display_name"/></tree>';
            await createViewEditor({
                serverData,
                type: "list",
                resModel: "coucou",
                arch: arch,
                mockRPC: function (route, args) {
                    if (route === "/web_studio/edit_view") {
                        assert.strictEqual(args.operations[0].new_attrs.readonly, "True");
                        assert.notOk("force_save" in args.operations[0].new_attrs);
                        changeArch(args.view_id, arch);
                    }
                },
            });

            await click(
                target.querySelector(".o_web_studio_list_view_editor [name='display_name']")
            );
            await click(target, ".o_web_studio_sidebar input#readonly");
        });
    }
);
