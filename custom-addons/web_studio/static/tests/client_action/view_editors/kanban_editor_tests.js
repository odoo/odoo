/** @odoo-module */

import { browser } from "@web/core/browser/browser";
import {
    getFixture,
    patchWithCleanup,
    click,
    dragAndDrop,
    nextTick,
} from "@web/../tests/helpers/utils";
import {
    createMockViewResult,
    createViewEditor,
    registerViewEditorDependencies,
    selectorContains,
    makeArchChanger,
} from "@web_studio/../tests/client_action/view_editors/view_editor_tests_utils";
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { registry } from "@web/core/registry";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { onWillRender } from "@odoo/owl";

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
                            display_name: { string: "Name", type: "char", store: true },
                            m2o: {
                                string: "Product",
                                type: "many2one",
                                relation: "product",
                                store: true,
                            },
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
        QUnit.module("Kanban");

        QUnit.test("empty kanban editor", async function (assert) {
            assert.expect(3);

            await createViewEditor({
                serverData,
                type: "kanban",
                resModel: "coucou",
                arch: `<kanban>
                    <templates>
                        <t t-name="kanban-box">
                        </t>
                    </templates>
                </kanban>
                `,
            });

            assert.containsOnce(target, ".o_kanban_renderer", "there should be a kanban editor");
            assert.containsNone(
                target,
                ".o_kanban_renderer .o-web-studio-editor--element-clickable",
                "there should be no node"
            );
            assert.containsNone(
                target,
                ".o_kanban_renderer .o_web_studio_hook",
                "there should be no hook"
            );
        });

        QUnit.test("kanban editor", async function (assert) {
            assert.expect(16);

            await createViewEditor({
                serverData,
                type: "kanban",
                resModel: "coucou",
                arch: `
                    <kanban>
                        <templates>
                            <t t-name='kanban-box'>
                                <div class='oe_kanban_card'>
                                    <field name='display_name'/>
                                </div>
                            </t>
                        </templates>
                    </kanban>`,
            });

            assert.containsN(target, ".o_kanban_record", 13);
            assert.containsN(target, ".o_kanban_record.o_kanban_demo", 6);
            assert.containsN(target, ".o_kanban_record.o_kanban_ghost", 6);
            assert.doesNotHaveClass(
                target.querySelectorAll(".o_kanban_record")[0],
                "o_kanban_ghost",
                "first record should not be a ghost"
            );
            assert.doesNotHaveClass(
                target.querySelectorAll(".o_kanban_record")[0],
                "o_kanban_demo",
                "first record should not be a demo"
            );
            assert.containsOnce(
                target,
                ".o_web_studio_kanban_view_editor .o-web-studio-editor--element-clickable",
                "there should be one node"
            );
            assert.hasClass(
                target.querySelector(
                    ".o_web_studio_kanban_view_editor .o-web-studio-editor--element-clickable"
                ),
                "o_web_studio_widget_empty",
                "the empty node should have the empty class"
            );
            assert.containsOnce(
                target,
                ".o_web_studio_kanban_view_editor .o_web_studio_hook",
                "there should be one hook"
            );
            assert.containsOnce(
                target,
                ".o_kanban_record .o_web_studio_add_kanban_tags",
                "there should be the hook for tags"
            );
            assert.containsOnce(
                target,
                ".o_kanban_record .o_web_studio_add_dropdown",
                "there should be the hook for dropdown"
            );
            assert.containsOnce(
                target,
                ".o_kanban_record .o_web_studio_add_priority",
                "there should be the hook for priority"
            );
            assert.containsOnce(
                target,
                ".o_kanban_record .o_web_studio_add_kanban_image",
                "there should be the hook for image"
            );

            await click(
                target.querySelector(
                    ".o_web_studio_kanban_view_editor .o-web-studio-editor--element-clickable"
                )
            );

            assert.strictEqual(
                target.querySelector(".o_web_studio_sidebar .nav-link.active").innerText,
                "Properties",
                "the Properties tab should now be active"
            );

            assert.hasClass(
                target.querySelector(
                    ".o_web_studio_kanban_view_editor .o-web-studio-editor--element-clickable"
                ),
                "o-web-studio-editor--element-clicked",
                "the field should have the clicked style"
            );

            assert.strictEqual(
                target.querySelector(".o_select_menu_toggler_slot").innerText,
                "Text (char)",
                "the widget in sidebar should be set by default"
            );

            assert.strictEqual(
                target.querySelector(".o_web_studio_property.o_web_studio_sidebar_text input")
                    .value,
                "Name",
                "the field should have the label Display Name in the sidebar"
            );
        });

        QUnit.test("no studio hook after a conditional field in the arch", async function (assert) {
            /*
             * When a condition is set directly on a field in the arch, no studio hook is pushed
             * meaning there is no way to put another field just after that one.
             * This is a requirement, otherwise the arch itself is at risk of being broken
             * ie: `<field t-elif="someCondifiton" /><field name="newField" /><t t-else=""/>`
             * is never valid.
             */
            serverData.models["coucou"].fields.xram = { type: "char", string: "xram" };
            serverData.models["coucou"].records = [{ id: 1 }];

            await createViewEditor({
                type: "kanban",
                serverData,
                resModel: "coucou",
                arch: `<kanban>
                    <field name="xram" />
                    <templates>
                        <t t-name='kanban-box'>
                            <div class='oe_kanban_card'>
                                <field t-if="record.xram.raw_value === 'lrak'" name='display_name'/>
                                <field t-elif="record.xram.raw_value === 'groucho'" name='display_name' />
                                <field t-else="" name='display_name' />
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            });
            assert.containsNone(target, ".o_kanban_record .o_web_studio_hook");
        });

        QUnit.test(
            "existing field section should be unfolded by default in kanban",
            async function (assert) {
                assert.expect(2);

                await createViewEditor({
                    serverData,
                    type: "kanban",
                    resModel: "coucou",
                    arch: `<kanban>
                <templates>
                    <t t-name="kanban-box">
                        <div class="o_kanban_record">
                            <field name="display_name"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
                });

                await click(target.querySelector(".o_web_studio_new"));
                assert.hasClass(
                    target.querySelector(".o_web_studio_existing_fields_header i"),
                    "fa-caret-down",
                    "should have a existing fields unfolded"
                );
                assert.isVisible(
                    target.querySelector(".o_web_studio_existing_fields_section"),
                    "the existing fields section should be visible"
                );
            }
        );

        QUnit.test("indulge if components are present in the arch", async function (assert) {
            await createViewEditor({
                type: "kanban",
                serverData,
                resModel: "coucou",
                arch: `<kanban>
                    <field name="display_name" />
                    <templates>
                        <t t-name='kanban-box'>
                            <div class='oe_kanban_card'>
                                <div class="rendered" />
                                <MyComponent t-props="someProps" />
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            });

            assert.containsOnce(target, ".rendered");
        });

        QUnit.test("undo when edition of kanban results in error", async function (assert) {
            let triggerError = false;

            patchWithCleanup(KanbanRecord.prototype, {
                setup() {
                    super.setup();
                    if (triggerError) {
                        onWillRender(() => {
                            triggerError = false;
                            throw new Error("Boom");
                        });
                    }
                },
            });

            const notificationService = {
                start() {
                    return { add: (message) => assert.step(`notification: ${message}`) };
                },
            };

            registry.category("services").add("notification", notificationService, { force: true });
            const changeArch = makeArchChanger();

            const arch = `
                <kanban>
                    <templates>
                        <t t-name='kanban-box'>
                            <div class='oe_kanban_card'>
                                <div class="rendered" />
                                <field name="display_name" />
                            </div>
                        </t>
                    </templates>
                </kanban>`;

            const errorArch = `
                <kanban>
                    <templates>
                        <t t-name='kanban-box'>
                            <div class='oe_kanban_card'>
                                <div class="rendered" />
                            </div>
                        </t>
                    </templates>
                </kanban>`;

            await createViewEditor({
                serverData,
                type: "kanban",
                resModel: "coucou",
                arch,
                mockRPC(route, args) {
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

            assert.containsOnce(target, ".rendered");
            // trigger an editView
            await click(target.querySelector(".o-web-studio-editor--element-clickable"));
            triggerError = true;
            await click(target.querySelector(".o_web_studio_sidebar .o_web_studio_remove"));
            await click(target.querySelector(".modal footer button"));
            assert.verifySteps([
                "edit_view",
                "notification: The requested change caused an error in the view. It could be because a field was deleted, but still used somewhere else.",
                "edit_view",
            ]);
            assert.containsOnce(target, ".rendered");
        });

        QUnit.test(
            "prevent crash when accessing details of implementation",
            async function (assert) {
                // the XML editor button is only available in debug mode
                const initialDebugMode = odoo.debug;
                odoo.debug = true;

                registerCleanup(() => {
                    odoo.debug = initialDebugMode;
                });

                const arch = `
                <kanban>
                    <templates>
                        <t t-name='kanban-box'>
                            <div class='oe_kanban_card'>
                                <div t-if="myDetailMethod()" />
                            </div>
                        </t>
                    </templates>
                </kanban>`;

                await createViewEditor({
                    type: "kanban",
                    serverData,
                    resModel: "coucou",
                    arch,
                    mockRPC(route, args) {
                        if (route === "/web_studio/get_xml_editor_resources") {
                            return Promise.resolve({
                                views: [
                                    {
                                        active: true,
                                        arch: arch,
                                        id: 99999999,
                                        inherit_id: false,
                                        name: "base view",
                                    },
                                    {
                                        active: true,
                                        arch: "<data/>",
                                        id: 42,
                                        inherit_id: 99999999,
                                        name: "studio view",
                                    },
                                ],
                                scss: [],
                                js: [],
                            });
                        }
                    },
                });
                await nextTick();
                assert.strictEqual(
                    target.querySelector(".o_kanban_record").textContent,
                    "Preview is not available"
                );

                await click(selectorContains(target, ".o_web_studio_sidebar .nav-link", "View"));
                await click(target, ".o_web_studio_sidebar .o_web_studio_open_xml_editor");
                await nextTick();
                assert.strictEqual(
                    target.querySelector(".o_kanban_record").textContent,
                    "Preview is not available"
                );
            }
        );

        QUnit.test("disable global click", async (assert) => {
            registry.category("services").add(
                "action",
                {
                    start() {
                        return {
                            doAction() {
                                assert.step("action done");
                            },
                            loadState() {},
                            doActionButton() {
                                assert.step("action done");
                            },
                        };
                    },
                },
                { force: true }
            );
            const arch = `
            <kanban action="42" type="object" >
                <field name="display_name" />
                <templates>
                    <t t-name='kanban-box'>
                        <div class='oe_kanban_card'/>
                    </t>
                </templates>
            </kanban>`;

            const vem = await createViewEditor({
                serverData,
                type: "kanban",
                resModel: "coucou",
                arch,
            });
            // sanity check
            vem.env.services.action.doAction();
            assert.verifySteps(["action done"]);

            await click(target.querySelector(".o_kanban_record"));
            assert.verifySteps([]);
        });

        QUnit.test("button with text node are correctly rendered", async (assert) => {
            const arch = `
            <kanban action="42" type="object" >
                <field name="display_name" />
                <templates>
                    <t t-name='kanban-box'>
                        <button type="object" name="42">Some action</button>
                    </t>
                </templates>
            </kanban>`;

            await createViewEditor({
                type: "kanban",
                serverData,
                resModel: "coucou",
                arch,
            });

            assert.strictEqual(
                target.querySelector(".o_kanban_record button").textContent,
                "Some action"
            );
        });

        QUnit.test("changing tab should reset the selected node", async function (assert) {
            serverData.models.coucou.records = [];
            await createViewEditor({
                serverData,
                type: "kanban",
                resModel: "coucou",
                arch: `<kanban>
                    <templates>
                        <t t-name='kanban-box'>
                            <div class='o_kanban_record'>
                                <field name='display_name' invisible='1'/>
                                <field name='priority'/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            });

            // switch tab to 'view' click on 'show invisible elements'
            await click(selectorContains(target, ".o_web_studio_sidebar .nav-link", "View"));
            await click(target.querySelector(".o_web_studio_sidebar input#show_invisible"));
            assert.containsNone(
                target,
                ".o-web-studio-editor--element-clickable.o-web-studio-editor--element-clicked",
                "the field should not have the clicked style"
            );

            // select field 'display_name'
            await click(
                target.querySelector(
                    ".o_web_studio_kanban_view_editor span.o-web-studio-editor--element-clickable[data-field-name='display_name']"
                )
            );
            assert.hasClass(
                target.querySelector(
                    ".o_web_studio_widget_empty.o-web-studio-editor--element-clickable"
                ),
                "o-web-studio-editor--element-clicked",
                "the field should have the clicked style"
            );

            // changing tab (should reset selected_node_id)
            await click(selectorContains(target, ".o_web_studio_sidebar .nav-link", "View"));
            assert.containsNone(
                target,
                ".o-web-studio-editor--element-clicked",
                "no clicked element is present"
            );

            // unchecked 'show invisible'
            await click(target.querySelector(".o_web_studio_sidebar input#show_invisible"));
            assert.containsNone(
                target,
                ".o-web-studio-editor--element-clicked",
                "the field should not have the clicked style"
            );
        });

        QUnit.test("kanban editor show invisible elements", async function (assert) {
            serverData.models.coucou.records = [];
            await createViewEditor({
                serverData,
                resModel: "coucou",
                type: "kanban",
                arch: `<kanban>
                    <templates>
                        <t t-name='kanban-box'>
                            <div class='o_kanban_record'>
                                <field name="display_name" invisible="1"/>
                                <field name="char_field" invisible="True"/>
                                <field name="priority" invisible="id != 1"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            });

            assert.containsNone(
                target,
                ".o_web_studio_kanban_view_editor .o-web-studio-editor--element-clickable",
                "there should be no visible node"
            );
            assert.hasAttrValue(
                target.querySelector("input#show_invisible"),
                "checked",
                undefined,
                "show invisible checkbox is not checked"
            );

            // click on 'show invisible elements
            await click(target.querySelector(".o_web_studio_sidebar input#show_invisible"));

            assert.containsN(
                target,
                ".o_web_studio_kanban_view_editor .o-web-studio-editor--element-clickable",
                3,
                "the 3 invisible fields should be visible now"
            );
            assert.containsN(
                target,
                ".o_web_studio_kanban_view_editor .o_web_studio_show_invisible.o-web-studio-editor--element-clickable",
                3,
                "the 3 fields should have the correct class for background"
            );
        });

        QUnit.test("kanban editor add priority", async function (assert) {
            const changeArch = makeArchChanger();

            const arch = `
            <kanban>
                <templates>
                    <t t-name='kanban-box'>
                        <div class='o_kanban_record'>
                            <field name='display_name'/>
                            <field name='priority' widget='priority'/>
                        </div>
                    </t>
                </templates>
            </kanban>`;

            await createViewEditor({
                type: "kanban",
                serverData,
                resModel: "coucou",
                arch: `<kanban>
                    <templates>
                        <t t-name='kanban-box'>
                            <div class='o_kanban_record'>
                              <field name='display_name'/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
                mockRPC: function (route, args) {
                    if (route === "/web_studio/get_default_value") {
                        return Promise.resolve({});
                    }
                    if (route === "/web_studio/edit_view") {
                        assert.step("edit_view");
                        assert.deepEqual(
                            args.operations[0],
                            {
                                field: "priority",
                                type: "kanban_priority",
                            },
                            "Proper field name and operation type should be passed"
                        );
                        changeArch(args.view_id, arch);
                    }
                },
            });

            assert.containsOnce(
                target,
                ".o_kanban_record .o_web_studio_add_priority",
                "there should be the hook for priority"
            );
            // click the 'Add a priority' link
            await click(target.querySelector(".o_kanban_record .o_web_studio_add_priority"));
            assert.containsOnce(target, `.modal .modal-body select > option[value="priority"]`);
            // select priority field from the drop-down
            const priorityOption = target.querySelector(
                '.modal .modal-body select > option[value="priority"]'
            );
            priorityOption.setAttribute("selected", true);
            priorityOption.dispatchEvent(new Event("change", { bubbles: true }));

            await click(target.querySelector(".modal .modal-footer .btn-primary"));
            assert.verifySteps(["edit_view"]);
            assert.containsOnce(
                target,
                ".o_field_priority",
                "there should be priority widget in kanban record"
            );
            assert.containsNone(
                target,
                ".o_kanban_record .o_web_studio_add_priority",
                "there should be no priority hook if priority widget exists on kanban"
            );
        });

        QUnit.test("kanban editor no avatar button if already in arch", async function (assert) {
            const arch = `
                <kanban>
                    <templates>
                        <field name="partner_id"/>
                        <t t-name='kanban-box'>
                            <field name="display_name"/>
                            <img
                                t-if="false"
                                t-att-src="kanban_image('res.partner', 'avatar_128', record.partner_id.raw_value)"
                                class="oe_kanban_avatar"/>
                        </t>
                    </templates>
                </kanban>
                `;

            serverData.models.coucou.fields.partner_id = {
                string: "Res Partner",
                type: "many2one",
                relation: "partner",
            };
            serverData.models.coucou.records = [{ id: 1, display_name: "Eleven", partner_id: 11 }];
            await createViewEditor({
                type: "kanban",
                serverData,
                resModel: "coucou",
                arch,
            });
            assert.containsNone(
                target,
                ".o_web_studio_add_kanban_image",
                "there should be no option to add an avatart"
            );
        });

        QUnit.test("kanban editor add and remove image", async function (assert) {
            // We have to add relational model specifically named 'res.parter' or
            // 'res.users' because it is hard-coded in the kanban record editor.
            serverData.models["res.partner"] = {
                fields: {
                    avatar_128: { type: "binary" },
                },
                records: [{ display_name: "Dustin", id: 1, avatar_128: "D Artagnan" }],
            };

            serverData.models.coucou.fields.partner_id = {
                string: "Res Partner",
                type: "many2one",
                relation: "res.partner",
            };
            serverData.models.coucou.records = [{ id: 1, display_name: "Eleven", partner_id: 11 }];

            const arch = `
                <kanban>
                    <templates>
                        <t t-name='kanban-box'>
                            <div class='o_kanban_record'>
                                <field name='display_name'/>
                            </div>
                        </t>
                    </templates>
                </kanban>`;

            const changeArch = makeArchChanger();
            let editViewCount = 0;
            await createViewEditor({
                serverData,
                type: "kanban",
                resModel: "coucou",
                arch: arch,
                mockRPC: function (route, args) {
                    if (route === "/web_studio/get_default_value") {
                        return Promise.resolve({});
                    }
                    if (route === "/web_studio/edit_view") {
                        assert.step("edit_view");
                        editViewCount++;
                        let newArch;
                        if (editViewCount === 1) {
                            assert.deepEqual(
                                args.operations[0],
                                {
                                    field: "partner_id",
                                    type: "kanban_image",
                                },
                                "Proper field name and operation type should be passed"
                            );
                            newArch = `<kanban>
                                <templates>
                                    <t t-name='kanban-box'>
                                        <div class='o_kanban_record'>
                                        <field name='display_name'/>
                                            <div class='oe_kanban_bottom_right'>
                                                <div>test</div><!-- dummy div to make sure img is deleted (otherwise parent div of only child will be deleted) -->
                                                <img t-att-src='kanban_image("res.partner", "avatar_128", 1)' class='oe_kanban_avatar float-end' width='24' height='24'/>
                                                </div>
                                             </div>
                                    </t>
                                </templates>
                            </kanban>`;
                        } else if (editViewCount === 2) {
                            assert.strictEqual(
                                args.operations[1].type,
                                "remove",
                                "Should have passed correct OP type"
                            );
                            assert.strictEqual(
                                args.operations[1].target.tag,
                                "img",
                                "Should have correct target tag"
                            );
                            assert.deepEqual(
                                args.operations[1].target.xpath_info,
                                [
                                    { tag: "kanban", indice: 1 },
                                    { tag: "templates", indice: 1 },
                                    { tag: "t", indice: 1 },
                                    { tag: "div", indice: 1 },
                                    { tag: "div", indice: 1 },
                                    { tag: "img", indice: 1 },
                                ],
                                "Should have correct xpath_info as we do not have any tag identifier attribute on image img"
                            );
                            newArch = arch;
                        }
                        changeArch(args.view_id, newArch);
                    }
                },
            });

            assert.containsOnce(
                target,
                ".o_kanban_record .o_web_studio_add_kanban_image",
                "there should be the hook for Image"
            );
            // click the 'Add a Image' link
            await click(target.querySelector(".o_kanban_record .o_web_studio_add_kanban_image"));
            assert.containsOnce(target, `.modal .modal-body select > option[value="partner_id"]`);

            // Click 'Confirm' Button
            await click(target.querySelector(".modal .modal-footer .btn-primary"));
            assert.verifySteps(["edit_view"]);
            const img = target.querySelectorAll(".oe_kanban_bottom_right img.oe_kanban_avatar");
            assert.strictEqual(img.length, 1, "there should be an avatar image");
            // Click on the image
            await click(img[0]);
            // remove image from sidebar
            await click(target.querySelector(".o_web_studio_sidebar .o_web_studio_remove"));
            assert.strictEqual(
                target.querySelector(".modal-body").textContent,
                "Are you sure you want to remove this img from the view?",
                "should display the correct message"
            );
            await click(target.querySelector(".modal-footer .btn-primary"));
            assert.verifySteps(["edit_view"]);
        });

        QUnit.test("kanban editor with widget", async function (assert) {
            await createViewEditor({
                serverData,
                type: "kanban",
                resModel: "coucou",
                arch: `<kanban>
                        <templates>
                            <t t-name='kanban-box'>
                            <div class='o_kanban_record'>
                                <field name='display_name' widget='email'/>
                            </div>
                            </t>
                        </templates>
                    </kanban>`,
            });

            assert.containsOnce(
                target,
                ".o_web_studio_kanban_view_editor .o-web-studio-editor--element-clickable",
                "there should be one node"
            );
            assert.containsOnce(
                target,
                ".o_web_studio_kanban_view_editor .o_web_studio_hook",
                "there should be one hook"
            );

            await click(
                target.querySelector(
                    ".o_web_studio_kanban_view_editor .o-web-studio-editor--element-clickable"
                )
            );

            assert.strictEqual(
                target.querySelector(
                    `.o_web_studio_sidebar .o_web_studio_property_widget .o_select_menu_toggler_slot`
                ).textContent,
                "Email (email)",
                "the widget in sidebar should be correctly set"
            );
            assert.strictEqual(
                target.querySelector(`.o_web_studio_sidebar input[name="string"]`).value,
                "Name",
                "the field should have the label Display Name in the sidebar"
            );
        });

        QUnit.test("grouped kanban editor", async function (assert) {
            serverData.models.coucou.records = [];
            await createViewEditor({
                type: "kanban",
                serverData,
                resModel: "coucou",
                arch: `<kanban default_group_by='display_name'>
                    <templates>
                        <t t-name='kanban-box'>
                            <div class='o_kanban_record'>
                                <field name='display_name'/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
                mockRPC(route, args) {
                    if (args.method == "web_read_group") {
                        assert.step("web_read_group");
                        assert.strictEqual(args.kwargs.limit, 1);
                    }
                }
            });
            assert.verifySteps(["web_read_group"]);

            assert.hasClass(
                target.querySelector(".o_web_studio_kanban_view_editor "),
                "o_kanban_grouped",
                "the editor should be grouped"
            );
            assert.containsOnce(
                target,
                ".o_web_studio_kanban_view_editor .o-web-studio-editor--element-clickable",
                "there should be one node"
            );
            assert.hasClass(
                target.querySelector(
                    ".o_web_studio_kanban_view_editor .o-web-studio-editor--element-clickable"
                ),
                "o_web_studio_widget_empty",
                "the empty node should have the empty class"
            );
            assert.containsOnce(
                target,
                ".o_web_studio_kanban_view_editor .o_web_studio_hook",
                "there should be one hook"
            );

            assert.containsNone(target, ".o_kanban_header_title");
            assert.containsNone(target, ".o_kanban_counter");
            assert.containsN(target, ".o_kanban_group", 2);
            assert.containsN(
                target,
                ".o_kanban_group:nth-child(1) .o_kanban_record.o_kanban_demo",
                6
            );
            assert.containsN(
                target,
                ".o_kanban_group:nth-child(2) .o_kanban_record.o_kanban_demo",
                7
            );
        });

        QUnit.test("grouped kanban editor with record", async function (assert) {
            serverData.models.coucou.records = [
                {
                    id: 1,
                    display_name: "coucou 1",
                },
            ];

            await createViewEditor({
                serverData,
                type: "kanban",
                resModel: "coucou",
                arch: `<kanban default_group_by='display_name'>
                        <templates>
                            <t t-name='kanban-box'>
                                <div class='o_kanban_record'>
                                <field name='display_name'/>
                                </div>
                            </t>
                        </templates>
                    </kanban>`,
            });

            assert.hasClass(
                target.querySelector(".o_web_studio_kanban_view_editor"),
                "o_kanban_grouped",
                "the editor should be grouped"
            );
            assert.containsOnce(
                target,
                ".o_web_studio_kanban_view_editor .o-web-studio-editor--element-clickable",
                "there should be one node"
            );
            assert.doesNotHaveClass(
                target.querySelector(
                    ".o_web_studio_kanban_view_editor .o-web-studio-editor--element-clickable"
                ),
                "o_web_studio_widget_empty",
                "the empty node should not have the empty class"
            );
            assert.containsOnce(
                target,
                ".o_web_studio_kanban_view_editor .o_web_studio_hook",
                "there should be one hook"
            );
        });

        QUnit.test("kanban editor, grouped on date field, no record", async function (assert) {
            serverData.models.coucou.fields.date = { name: "date", type: "date", string: "Date" };
            serverData.models.coucou.records = [];

            await createViewEditor({
                serverData,
                type: "kanban",
                resModel: "coucou",
                arch: `
                <kanban default_group_by='date'>
                    <templates>
                        <t t-name='kanban-box'>
                            <div><field name='display_name'/></div>
                        </t>
                    </templates>
                </kanban>`,
            });

            assert.hasClass(
                target.querySelector(".o_web_studio_kanban_view_editor"),
                "o_kanban_grouped"
            );
            assert.containsOnce(target, ".o_kanban_record:not(.o_kanban_demo)");
        });

        QUnit.test(
            "kanban editor, grouped on date field granular, no record, progressbar",
            async function (assert) {
                serverData.models.coucou.fields.date = {
                    name: "date",
                    type: "date",
                    string: "Date",
                };
                serverData.models.coucou.records = [];
                patchWithCleanup(odoo, {
                    debug: true,
                });

                const arch = `
            <kanban default_group_by='date:month'>
                <progressbar colors="{}" field="priority"/>
                <field name="priority" />
                <templates>
                    <t t-name='kanban-box'>
                        <div><field name='display_name'/></div>
                    </t>
                </templates>
            </kanban>`;
                await createViewEditor({
                    serverData,
                    type: "kanban",
                    resModel: "coucou",
                    arch,
                    mockRPC: (route, args) => {
                        if (route === "/web_studio/get_xml_editor_resources") {
                            return {
                                views: [
                                    {
                                        id: 99999999,
                                        name: "default",
                                        arch,
                                    },
                                ],
                                main_view_key: "",
                            };
                        }
                        if (route.endsWith("/web/bundle/web.ace_lib")) {
                            return [{}];
                        }
                    },
                });

                assert.hasClass(
                    target.querySelector(".o_web_studio_kanban_view_editor"),
                    "o_kanban_grouped"
                );
                assert.containsOnce(target, ".o_kanban_record:not(.o_kanban_demo)");
                await click(target, "button.o_web_studio_open_xml_editor");
                assert.containsOnce(target, ".o_web_studio_xml_editor");
                assert.containsOnce(target, ".o_view_controller.o_kanban_view");
            }
        );

        QUnit.test("Remove a drop-down menu using kanban editor", async function (assert) {
            const arch = `
            <kanban>
                <templates>
                    <t t-name="kanban-menu">
                        <a type="edit" class="dropdown-item">Edit</a>
                    </t>
                    <t t-name="kanban-box">
                        <div>
                            <div>
                                <field name="display_name"/>
                            </div>
                        </div>
                    </t>
                </templates>
            </kanban>`;
            await createViewEditor({
                type: "kanban",
                serverData,
                resModel: "coucou",
                arch,
                mockRPC: function (route, args) {
                    if (route === "/web_studio/edit_view") {
                        assert.step("edit_view");
                        assert.strictEqual(
                            args.operations[0].type,
                            "remove",
                            "Should have passed correct OP type"
                        );
                        assert.strictEqual(
                            args.operations[0].target.tag,
                            "t",
                            "Should have correct target tag"
                        );
                        assert.deepEqual(
                            args.operations[0].target.xpath_info,
                            [
                                { tag: "kanban", indice: 1 },
                                { tag: "templates", indice: 1 },
                                { tag: "t", indice: 1 },
                            ],
                            "Should have correct xpath_info as we do not have any tag identifier attribute on drop-down div"
                        );
                    }
                },
            });
            assert.containsOnce(target, ".o_dropdown_kanban", "there should be one dropdown node");
            await click(target.querySelector(".o_dropdown_kanban"));
            // remove drop-down from sidebar
            await click(target.querySelector(".o_web_studio_sidebar .o_web_studio_remove"));
            assert.strictEqual(
                target.querySelector(".modal-body").textContent,
                "Are you sure you want to remove this dropdown from the view?",
                "should display the correct message"
            );
            await click(target.querySelector(".modal .btn-primary"));
            assert.verifySteps(["edit_view"]);
        });

        QUnit.test(
            'kanban editor remove "Set Cover Image" from dropdown menu',
            async function (assert) {
                serverData.models["ir.attachment"] = {
                    fields: {},
                    records: [],
                };

                serverData.models["partner"].fields.displayed_image_id = {
                    string: "cover",
                    type: "many2one",
                    relation: "ir.attachment",
                };

                const arch = `
                <kanban>
                    <templates>
                        <t t-name="kanban-menu">
                            <a type="set_cover">Set Cover Image</a>
                        </t>
                        <t t-name='kanban-box'>
                            <div class='o_kanban_record'>
                                <field name='displayed_image_id' widget='attachment_image'/>
                            </div>
                        </t>
                    </templates>
                </kanban>`;

                await createViewEditor({
                    serverData,
                    type: "kanban",
                    resModel: "partner",
                    arch,
                    mockRPC: function (route, args) {
                        if (route === "/web_studio/edit_view") {
                            assert.step("edit_view");
                        }
                        if (
                            route === "/web_studio/edit_view" &&
                            args.operations[0].type === "remove"
                        ) {
                            assert.deepEqual(
                                args.operations[0],
                                {
                                    target: {
                                        attrs: { name: "displayed_image_id" },
                                        tag: "field",
                                        extra_nodes: [
                                            {
                                                tag: "a",
                                                attrs: {
                                                    type: "set_cover",
                                                },
                                            },
                                        ],
                                    },
                                    type: "remove",
                                },
                                "Proper field name and operation type should be passed"
                            );
                        }
                    },
                });

                // used to generate fields view in mockRPC
                await click(target.querySelector(".o_kanban_record .o_dropdown_kanban"));
                await click(target.querySelector(".o_web_studio_sidebar .o-checkbox #cover_value"));
                assert.verifySteps(["edit_view"]);
            }
        );

        QUnit.test(
            'kanban editor add "Set Cover Image" option in dropdown menu',
            async function (assert) {
                serverData.models["ir.attachment"] = {
                    fields: {},
                    records: [],
                };

                serverData.models["partner"].fields.displayed_image_id = {
                    string: "cover",
                    type: "many2one",
                    relation: "ir.attachment",
                };
                const arch = `
                <kanban>
                    <templates>
                        <t t-name='kanban-menu'/>
                        <t t-name='kanban-box'>
                            <div class='o_kanban_record'>
                            </div>
                        </t>
                    </templates>
                </kanban>`;
                await createViewEditor({
                    serverData,
                    type: "kanban",
                    resModel: "partner",
                    arch,
                    mockRPC: function (route, args) {
                        if (route === "/web_studio/edit_view") {
                            assert.step("edit_view");
                            assert.deepEqual(
                                args.operations[0],
                                { field: "displayed_image_id", type: "kanban_set_cover" },
                                "Proper field name and operation type should be passed"
                            );
                        }
                    },
                });

                await click(target.querySelector(".o_kanban_record .o_dropdown_kanban"));
                assert.hasAttrValue(
                    target.querySelector('.o_web_studio_sidebar input[id="cover_value"]'),
                    "checked",
                    undefined,
                    "Option to set cover should not be enabled"
                );
                await click(target.querySelector('.o_web_studio_sidebar input[id="cover_value"]'));
                assert.containsOnce(
                    target,
                    '.modal .modal-body select option[value="displayed_image_id"]'
                );

                // Select the field for cover image
                const fieldForCover = target.querySelector(".modal .modal-body select");
                fieldForCover.value = "displayed_image_id";
                fieldForCover.dispatchEvent(new Event("change", { bubbles: true }));
                // Click the confirm button
                await click(target.querySelector(".modal .modal-footer .btn-primary"));
                assert.verifySteps(["edit_view"]);
            }
        );

        QUnit.test("drag and drop a new field", async (assert) => {
            const newArch = `
            <kanban>
                <templates>
                    <t t-name='kanban-box'>
                        <div class='oe_kanban_card'>
                            <field name='display_name'/>
                            <field name='char_field' display="full" />
                        </div>
                    </t>
                </templates>
            </kanban>`;

            const changeArch = makeArchChanger();

            await createViewEditor({
                serverData,
                type: "kanban",
                resModel: "coucou",
                arch: `<kanban>
                    <templates>
                        <t t-name='kanban-box'>
                            <div class='oe_kanban_card'>
                                <field name='display_name'/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
                mockRPC: function (route, args) {
                    if (route === "/web_studio/edit_view") {
                        assert.step("edit_view");
                        assert.deepEqual(args.operations[0], {
                            node: {
                                attrs: {
                                    display: "full",
                                    name: "char_field",
                                },
                                tag: "field",
                            },
                            position: "after",
                            target: {
                                attrs: {
                                    name: "display_name",
                                },
                                tag: "field",
                                xpath_info: [
                                    {
                                        indice: 1,
                                        tag: "kanban",
                                    },
                                    {
                                        indice: 1,
                                        tag: "templates",
                                    },
                                    {
                                        indice: 1,
                                        tag: "t",
                                    },
                                    {
                                        indice: 1,
                                        tag: "div",
                                    },
                                    {
                                        indice: 1,
                                        tag: "field",
                                    },
                                ],
                            },
                            type: "add",
                        });
                        changeArch(args.view_id, newArch);
                    }
                },
            });
            await click(selectorContains(target, ".o_web_studio_sidebar .nav-link", "Add"));

            await dragAndDrop(
                selectorContains(
                    target,
                    ".o_web_studio_existing_fields .o_web_studio_component.o_web_studio_field_char",
                    "A char"
                ),
                target.querySelector(".o_web_studio_kanban_view_editor .o_web_studio_hook")
            );
            assert.verifySteps(["edit_view"]);
        });

        QUnit.test("placeholder for set but empty avatar", async (assert) => {
            serverData.models["coucou"].fields.avatar = { type: "binary", string: "A vatar" };
            serverData.models["coucou"].records = [
                {
                    id: 1,
                    avatar: false,
                },
            ];

            await createViewEditor({
                serverData,
                resModel: "coucou",
                type: "kanban",
                arch: `<kanban>
                    <field name="avatar" invisible="1"/>
                    <templates>
                        <t t-name='kanban-box'>
                            <div class='oe_kanban_card'>
                               <t name="user_avatar" t-if="record.avatar.raw_value">
                                    <img t-att-src="kanban_image('coucou', 'avatar', record.avatar.raw_value)" class="oe_kanban_avatar" alt="Avatar"/>
                                </t>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            });
            assert.containsNone(target, "img.oe_kanban_avatar");
            assert.containsOnce(target, "span.oe_kanban_avatar");
        });

        QUnit.test("add tags with no many2many field", async (assert) => {
            const coucouFieldsFiltered = Object.entries(serverData.models["coucou"].fields).filter(
                ([fname, field]) => !field.type === "many2many"
            );
            serverData.models["coucou"].fields = Object.fromEntries(coucouFieldsFiltered);

            await createViewEditor({
                serverData,
                resModel: "coucou",
                type: "kanban",
                arch: `<kanban>
                    <templates>
                        <t t-name='kanban-box'>
                            <div class='oe_kanban_card' />
                        </t>
                    </templates>
                </kanban>`,
            });
            await click(target, ".o_web_studio_add_kanban_tags");
            assert.containsOnce(target, ".modal");
            assert.strictEqual(
                target.querySelector(".modal-body").textContent,
                "You first need to create a many2many field in the form view."
            );
        });

        QUnit.test("add tags", async (assert) => {
            const changeArch = makeArchChanger();
            serverData.models["coucou"].fields.m2m = {
                type: "many2many",
                string: "many 2 many",
                relation: "partner",
            };
            const newArch = `
            <kanban>
                <templates>
                    <t t-name='kanban-box'>
                        <div class='oe_kanban_card'>
                             <field name="m2m"/>
                        </div>
                    </t>
                </templates>
            </kanban>`;

            await createViewEditor({
                serverData,
                resModel: "coucou",
                type: "kanban",
                arch: `<kanban>
                    <templates>
                        <t t-name='kanban-box'>
                            <div class='oe_kanban_card' />
                        </t>
                    </templates>
                </kanban>`,

                mockRPC: function (route, args) {
                    if (route === "/web_studio/edit_view") {
                        assert.step("edit_view");
                        assert.deepEqual(args.operations[0], {
                            node: {
                                attrs: {
                                    name: "m2m",
                                },
                                tag: "field",
                            },
                            position: "inside",
                            target: {
                                attrs: {
                                    class: "oe_kanban_card",
                                },
                                tag: "div",
                                xpath_info: [
                                    {
                                        indice: 1,
                                        tag: "kanban",
                                    },
                                    {
                                        indice: 1,
                                        tag: "templates",
                                    },
                                    {
                                        indice: 1,
                                        tag: "t",
                                    },
                                    {
                                        indice: 1,
                                        tag: "div",
                                    },
                                ],
                            },
                            type: "add",
                        });
                        changeArch(args.view_id, newArch);
                    }
                },
            });
            await click(target, ".o_web_studio_add_kanban_tags");
            await click(target.querySelector(".modal .modal-footer .btn-primary"));
            assert.verifySteps(["edit_view"]);
            assert.containsNone(target, ".o_web_studio_add_kanban_tags");
        });

        QUnit.test("add dropdown", async (assert) => {
            const changeArch = makeArchChanger();
            const newArch = `
            <kanban>
                <templates>
                    <t t-name='kanban-menu'>
                        <t t-if="widget.editable">
                            <a type="edit" class="dropdown-item">Edit</a>
                        </t>
                        <t t-if="widget.deletable">
                            <a type="delete" class="dropdown-item">Delete</a>
                        </t>
                        <ul class="oe_kanban_colorpicker" data-field="x_color"/>
                    </t>
                    <t t-name='kanban-box'>
                        <div class='oe_kanban_card'>
                        </div>
                    </t>
                </templates>
            </kanban>`;

            await createViewEditor({
                serverData,
                resModel: "coucou",
                type: "kanban",
                arch: `<kanban>
                    <templates>
                        <t t-name='kanban-box'>
                            <div class='oe_kanban_card' />
                        </t>
                    </templates>
                </kanban>`,

                mockRPC: function (route, args) {
                    if (route === "/web_studio/edit_view") {
                        assert.step("edit_view");
                        assert.deepEqual(args.operations[0], {
                            type: "kanban_dropdown",
                        });
                        changeArch(args.view_id, newArch);
                    }
                },
            });
            await click(target, ".o_web_studio_add_dropdown");
            await click(target.querySelector(".modal .modal-footer .btn-primary"));
            assert.verifySteps(["edit_view"]);
            assert.containsNone(target, ".o_web_studio_add_dropdown");
        });

        QUnit.test("kanban: onchange is resilient to errors", async (assert) => {
            await createViewEditor({
                serverData,
                type: "kanban",
                resModel: "coucou",
                arch: `
            <kanban>
                <templates>
                    <t t-name="kanban-box">
                        <div class="rendered">
                            <field name="display_name" />
                        </div>
                    </t>
                </templates>
            </kanban>`,
                mockRPC(route, args) {
                    if (args.method === "onchange") {
                        assert.step("onchange");
                        throw new Error("Boom");
                    }
                },
            });

            assert.verifySteps(["onchange"]);
            assert.containsOnce(target, ".rendered");
        });

        QUnit.test("kanban: onchange is resilient to errors -- debug mode", async (assert) => {
            const _console = window.console;
            window.console = Object.assign(Object.create(_console), {
                warn(msg) {
                    assert.step(msg);
                },
            });
            registerCleanup(() => {
                window.console = _console;
            });
            patchWithCleanup(odoo, {
                debug: true,
            });
            await createViewEditor({
                serverData,
                type: "kanban",
                resModel: "coucou",
                arch: `
            <kanban>
                <templates>
                    <t t-name="kanban-box">
                        <div class="rendered">
                            <field name="display_name" />
                        </div>
                    </t>
                </templates>
            </kanban>`,
                mockRPC(route, args) {
                    if (args.method === "onchange") {
                        assert.step("onchange");
                        throw new Error("Boom");
                    }
                },
            });

            assert.verifySteps([
                "onchange",
                "The onchange triggered an error. It may indicate either a faulty call to onchange, or a faulty model python side",
            ]);
            assert.containsOnce(target, ".rendered");
        });

        QUnit.test("toggle create attribute", async function (assert) {
            assert.expect(2);
            let newCreateAttr;

            await createViewEditor({
                serverData,
                type: "kanban",
                resModel: "coucou",
                arch: `<kanban>
                    <templates>
                        <t t-name="kanban-box">
                        </t>
                    </templates>
                </kanban>
                `,
                async mockRPC(route, args) {
                    if (route === "/web_studio/edit_view") {
                        newCreateAttr = args.operations[0].new_attrs.create;
                    }
                },
            });

            assert.containsOnce(target, ".o_kanban_renderer", "there should be a kanban editor");
            await click(target.querySelector('input[name="create"]'));
            assert.strictEqual(newCreateAttr, false);
        });

        QUnit.test("toggle bold attribute", async (assert) => {
            const newArch = `
            <kanban>
                <templates>
                    <t t-name='kanban-box'>
                        <div class='oe_kanban_card'>
                            <field name='display_name' bold="True"/>
                        </div>
                    </t>
                </templates>
            </kanban>`;

            const changeArch = makeArchChanger();

            await createViewEditor({
                type: "kanban",
                serverData,
                resModel: "coucou",
                arch: `<kanban>
                <templates>
                    <t t-name='kanban-box'>
                        <div class='oe_kanban_card'>
                            <field name='display_name'/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
                mockRPC: function (route, args) {
                    if (route === "/web_studio/edit_view") {
                        assert.step("edit_view");
                        assert.deepEqual(args.operations[0], {
                            type: "attributes",
                            target: {
                                tag: "field",
                                attrs: { name: "display_name" },
                                xpath_info: [
                                    { tag: "kanban", indice: 1 },
                                    { tag: "templates", indice: 1 },
                                    { tag: "t", indice: 1 },
                                    { tag: "div", indice: 1 },
                                    { tag: "field", indice: 1 },
                                ],
                            },
                            position: "attributes",
                            node: {
                                tag: "field",
                                attrs: { name: "display_name" },
                            },
                            new_attrs: { bold: true },
                        });
                        changeArch(args.view_id, newArch);
                    }
                },
            });

            assert.containsNone(target, ".o_text_bold[data-field-name=display_name]");
            await click(target, "[data-field-name=display_name]");

            assert.strictEqual(
                target.querySelector(".o_web_studio_sidebar input[name='bold']").checked,
                false
            );

            await click(target, ".o_web_studio_sidebar input[name='bold']");
            assert.verifySteps(["edit_view"]);
            assert.containsOnce(target, ".o_text_bold[data-field-name=display_name]");
            await click(target, "[data-field-name=display_name]");
            assert.strictEqual(
                target.querySelector(".o_web_studio_sidebar input[name='bold']").checked,
                true
            );
        });

        QUnit.test("disallow using activeFields for the kanban priority", async function (assert) {
            assert.expect(2);

            serverData.models.coucou.fields.another_selection = {
                string: "Another selection",
                type: "selection",
                manual: true,
                selection: [
                    ["1", "Low"],
                    ["2", "Medium"],
                    ["3", "High"],
                ],
            };

            await createViewEditor({
                type: "kanban",
                serverData,
                resModel: "coucou",
                arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div class="o_kanban_record">
                                <field name="display_name"/>
                                <field name="another_selection"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            });

            await click(target, ".o_web_studio_add_priority");

            assert.containsOnce(document.body, ".o_web_studio_kanban_helper");

            assert.deepEqual(
                Array.prototype.map.call(
                    document.querySelectorAll(".o_web_studio_kanban_helper select option"),
                    (e) => e.value
                ),
                ["", "priority"]
            );
        });

        QUnit.test(
            "Default group by shows the right field choices and the value updates properly",
            async function (assert) {
                assert.expect(5);
                const startArch = `
                    <kanban>
                        <templates>
                            <t t-name='kanban-box'>
                                <div class='oe_kanban_card'>
                                    <field name='display_name'/>
                                </div>
                            </t>
                        </templates>
                    </kanban>
                `;
                const modifiedArch = `
                    <kanban default_group_by="display_name">
                        <templates>
                            <t t-name='kanban-box'>
                                <div class='oe_kanban_card'>
                                    <field name='display_name'/>
                                </div>
                            </t>
                        </templates>
                    </kanban>
                `;

                const changeArch = makeArchChanger();
                await createViewEditor({
                    serverData,
                    type: "kanban",
                    resModel: "coucou",
                    arch: startArch,
                    mockRPC: function (route, args) {
                        if (route === "/web_studio/edit_view") {
                            assert.deepEqual(args.operations[0], {
                                new_attrs: {
                                    default_group_by: "display_name",
                                },
                                position: "attributes",
                                type: "attributes",
                                target: {
                                    attrs: {},
                                    isSubviewAttr: true,
                                    tag: "kanban",
                                    xpath_info: [
                                        {
                                            indice: 1,
                                            tag: "kanban",
                                        },
                                    ],
                                },
                            });
                            assert.step("edit_view");
                            changeArch(args.view_id, modifiedArch);
                        }
                    },
                });

                await click(target, ".o_notebook_headers .nav-item:nth-child(2)");
                await click(
                    target,
                    ".o_web_studio_property_default_group_by .o_select_menu_toggler"
                );
                assert.containsN(target, ".o_select_menu_item", 2);

                await click(target, ".o_select_menu_item:nth-child(1)");
                assert.verifySteps(["edit_view"]);
                assert.equal(
                    target.querySelector(
                        ".o_web_studio_property_default_group_by .o_select_menu_toggler_slot"
                    ).innerText,
                    "Name",
                    "The field is properly selected as default group by"
                );
            }
        );

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
                type: "kanban",
                resModel: "coucou",
                arch: `<kanban>
                    <templates>
                    <t t-name="kanban-box">
                        <div>
                            <field name="product_ids" invisible="True" /><field name="m2o" invisible="True" />
                        </div>
                    </t>
                    </templates>
                    </kanban>`,
                mockRPC,
            });

            assert.deepEqual(
                Array.from(target.querySelectorAll(".o_kanban_record [data-field-name]")).map(
                    (el) => el.innerText
                ),
                []
            );
            await click(selectorContains(target, ".o_web_studio_sidebar .nav-link", "View"));
            await click(target, ".o_web_studio_sidebar #show_invisible");
            assert.deepEqual(
                Array.from(target.querySelectorAll(".o_kanban_record [data-field-name]")).map(
                    (el) => el.innerText
                ),
                ["1 record", "A very good product"]
            );
            assert.verifySteps(["web_search_read"]);
        });

        QUnit.test("editing 'quick_create' attribute updates the UI", async function (assert) {
            assert.expect(5);

            await createViewEditor({
                type: "kanban",
                serverData,
                resModel: "coucou",
                arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div class="o_kanban_record">
                                <field name="display_name"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
                mockRPC: {
                    "/web_studio/edit_view": (route, { operations }) => {
                        assert.step("edit_view");
                        assert.deepEqual(operations[0].new_attrs, {
                            quick_create: false,
                        });
                        const newArch = `
                        <kanban quick_create='false'>
                            <templates>
                                <t t-name="kanban-box">
                                    <div class="o_kanban_record">
                                        <field name="display_name"/>
                                    </div>
                                </t>
                            </templates>
                        </kanban>`;
                        return createMockViewResult(serverData, "kanban", newArch, "coucou");
                    },
                },
            });

            const checkbox = target.querySelector(".o_web_studio_property #quick_create");
            assert.strictEqual(checkbox.checked, true);

            await click(checkbox);
            assert.verifySteps(["edit_view"]);
            assert.strictEqual(checkbox.checked, false);
        });

        QUnit.test("fields present in the xml but absent from the 'kanban-box' template are listed in the sidebar", async function (assert) {
            await createViewEditor({
                type: "kanban",
                serverData,
                resModel: "coucou",
                arch: `
                <kanban>
                    <field name='char_field' display="full" />
                    <templates>
                        <t t-name="kanban-box">
                            <div class="o_kanban_record">
                                <field name="display_name"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            });
            await click(selectorContains(target, ".o_web_studio_sidebar .nav-link", "Add"));
            assert.containsOnce(
                target,
                '.o_web_studio_component[data-drop=\'{"fieldName":"char_field"}\']',
                "field is listed in the list of existing fields not present in the view"
            );
            assert.containsNone(
                target,
                '.o_web_studio_component[data-drop=\'{"fieldName":"display_name"}\']',
                "field is not listed in the list of existing fields not present in the view"
            );
        });
    }
);
