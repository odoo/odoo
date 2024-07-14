/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { browser } from "@web/core/browser/browser";
import {
    click,
    getFixture,
    nextTick,
    patchWithCleanup,
    editInput,
    dragAndDrop,
    drag,
} from "@web/../tests/helpers/utils";
import { click as asyncClick, contains } from "@web/../tests/utils";
import {
    createViewEditor,
    registerViewEditorDependencies,
    createMockViewResult,
    editAnySelect,
    disableHookAnimation,
    selectorContains,
} from "@web_studio/../tests/client_action/view_editors/view_editor_tests_utils";

import { ImageField } from "@web/views/fields/image/image_field";
import { createEnterpriseWebClient } from "@web_enterprise/../tests/helpers";
import { doAction } from "@web/../tests/webclient/helpers";
import { openStudio, registerStudioDependencies } from "../../helpers";
import { registry } from "@web/core/registry";
import { makeArchChanger } from "./view_editor_tests_utils";
import { start } from "@mail/../tests/helpers/test_utils";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { RPCError } from "@web/core/network/rpc_service";
import { setupManager } from "@mail/../tests/helpers/webclient_setup";
import { Component, EventBus, onMounted, xml } from "@odoo/owl";
import { fieldService } from "@web/core/field_service";
import { Setting } from "@web/views/form/setting/setting";

/** @type {Node} */
let target;
let serverData;

function currentSidebarTab() {
    return target.querySelector(".o_web_studio_sidebar .nav-link.active").innerText;
}

async function notebookRestoreElement() {
    // wait for the tab to be restored, then a potential element inside
    await nextTick();
    await nextTick();
}

const fakeMultiTab = {
    start() {
        const bus = new EventBus();
        return {
            bus,
            get currentTabId() {
                return null;
            },
            isOnMainTab() {
                return true;
            },
            getSharedValue(key, defaultValue) {
                return "";
            },
            setSharedValue(key, value) {},
            removeSharedValue(key) {},
        };
    },
};

const fakeImStatusService = {
    start() {
        return {
            registerToImStatus() {},
            unregisterFromImStatus() {},
        };
    },
};

function getFormEditorServerData() {
    return {
        models: {
            coucou: {
                fields: {
                    id: { string: "Id", type: "integer" },
                    display_name: { string: "Name", type: "char" },
                    m2o: { string: "Product", type: "many2one", relation: "product" },
                    char_field: { type: "char", string: "A char" },
                },
                records: [
                    {
                        id: 1,
                        display_name: "Kikou petite perruche",
                        m2o: 1,
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
                    empty_image: { string: "Image", type: "binary" },
                },
                records: [
                    {
                        id: 1,
                        display_name: "jean",
                        image: {},
                    },
                ],
            },
            "ir.model.fields": {
                fields: {
                    id: { string: "Id", type: "integer" },
                    display_name: { string: "Name", type: "char" },
                    relation: { string: "Relation", type: "char" },
                    ttype: { string: "Type", type: "char" },
                    store: { string: "Store", type: "boolean" },
                },
                records: [
                    {
                        id: 1,
                        display_name: "Select me",
                        relation: "coucou",
                        ttype: "many2one",
                        store: true,
                    },
                ],
            },
        },
        views: {
            "ir.model.fields,false,list": `<tree><field name="display_name"/></tree>`,
            "ir.model.fields,false,search": `<search><field name="display_name"/></search>`,
        },
    };
}

QUnit.module("View Editors", (hooks) => {
    hooks.beforeEach(() => {
        serverData = getFormEditorServerData();
        registerViewEditorDependencies();
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });
        target = getFixture();

        registry.category("services").add("multi_tab", fakeMultiTab, { force: true });
        registry.category("services").add("im_status", fakeImStatusService, { force: true });
    });
    QUnit.module("Form");

    QUnit.test(
        "Form editor should contains the view and the editor sidebar",
        async function (assert) {
            await createViewEditor({
                serverData,
                type: "form",
                resModel: "coucou",
                arch: /*xml*/ `
                        <form>
                            <sheet>
                                <field name="name"/>
                            </sheet>
                        </form>
                    `,
            });

            assert.containsOnce(
                target,
                ".o_web_studio_editor_manager .o_web_studio_view_renderer",
                "There should be one view renderer"
            );
            assert.containsOnce(
                target,
                ".o_web_studio_editor_manager .o_web_studio_sidebar",
                "There should be one sidebar"
            );
        }
    );

    QUnit.test("empty form editor", async function (assert) {
        assert.expect(3);

        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch: "<form/>",
        });

        assert.containsOnce(
            target,
            ".o_web_studio_form_view_editor",
            "there should be a form editor"
        );
        assert.containsNone(
            target,
            ".o_web_studio_form_view_editor .o-web-studio-editor--element-clickable",
            "there should be no node"
        );
        assert.containsNone(
            target,
            ".o_web_studio_form_view_editor .o_web_studio_hook",
            "there should be no hook"
        );
    });

    QUnit.test("Form editor view buttons can be set to invisible", async function (assert) {
        await createViewEditor({
            serverData,
            mockRPC: function (route, args) {
                if (route === "/web_studio/edit_view") {
                    assert.deepEqual(args.operations[0].target.xpath_info, [
                        {
                            tag: "form",
                            indice: 1,
                        },
                        {
                            tag: "header",
                            indice: 1,
                        },
                        {
                            tag: "button",
                            indice: 1,
                        },
                    ]);
                    assert.deepEqual(args.operations[0].new_attrs, { invisible: "True" });
                    assert.step("edit view");
                }
            },
            type: "form",
            resModel: "coucou",
            arch: /*xml*/ `
                        <form>
                            <header>
                                <button string="Test" type="object" class="oe_highlight"/>
                            </header>
                            <sheet>
                                <field name="name"/>
                            </sheet>
                        </form>
                    `,
        });

        assert.containsOnce(
            target,
            ".o_web_studio_editor_manager .o_web_studio_view_renderer",
            "There should be one view renderer"
        );
        assert.containsOnce(
            target,
            ".o_web_studio_editor_manager .o_web_studio_sidebar",
            "There should be one sidebar"
        );

        await click(target, ".o_form_renderer .o_statusbar_buttons > button");
        await click(target, ".o_notebook #invisible");
        assert.verifySteps(["edit view"]);
    });

    QUnit.test("optional field not in form editor", async function (assert) {
        assert.expect(1);

        await createViewEditor({
            serverData,
            type: "form",
            arch: `
                    <form>
                        <sheet>
                            <field name="display_name"/>
                        </sheet>
                    </form>`,
            resModel: "coucou",
        });

        await click(target, ".o_web_studio_view_renderer .o_field_char");
        assert.containsNone(
            target,
            ".o_web_studio_sidebar_optional_select",
            "there shouldn't be an optional field"
        );
    });

    QUnit.test("many2one field edition", async function (assert) {
        assert.expect(3);

        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch: `
                    <form>
                        <sheet>
                            <field name="m2o"/>
                        </sheet>
                    </form>
                `,
            resId: 1,
            mockRPC: function (route, args) {
                if (route === "/web_studio/get_studio_view_arch") {
                    return { studio_view_arch: "" };
                }
                if (route === "/web_studio/edit_view") {
                    return {};
                }
                if (route === "/web_studio/edit_view_arch") {
                    return {};
                }
                if (args.method === "get_formview_action") {
                    throw new Error("The many2one form view should not be opened");
                }
            },
        });

        assert.containsOnce(
            target,
            ".o_web_studio_form_view_editor .o-web-studio-editor--element-clickable",
            "there should be one node"
        );

        // edit the many2one
        await click(
            target,
            ".o_web_studio_form_view_editor .o-web-studio-editor--element-clickable",
            true
        );
        await nextTick();

        assert.ok(
            target.querySelectorAll(".o_web_studio_sidebar .o_web_studio_property").length > 0,
            "the sidebar should now display the field properties"
        );

        // TODO: Adapt to new studio
        // assert.containsOnce(target, '.o_web_studio_sidebar select[name="widget"] option[value="selection"]',
        //     "the widget in selection should be supported in m2o");
        assert.hasClass(
            target.querySelector(
                ".o_web_studio_form_view_editor .o-web-studio-editor--element-clickable"
            ),
            "o-web-studio-editor--element-clicked",
            "the column should have the clicked style"
        );
    });

    QUnit.test("image field is the placeholder when record is empty", async function (assert) {
        assert.expect(2);

        const arch = `
                <form>
                    <sheet>
                        <field name='empty_image' widget='image'/>
                    </sheet>
                </form>
            `;

        await createViewEditor({
            serverData,
            resModel: "partner",
            arch: arch,
            resId: 1,
            type: "form",
        });

        assert.containsOnce(
            target,
            ".o_web_studio_form_view_editor .o_field_image",
            "there should be one image"
        );

        assert.strictEqual(
            target
                .querySelector(".o_web_studio_form_view_editor .o_field_image img")
                .getAttribute("data-src"),
            "/web/static/img/placeholder.png",
            "default image in empty record should be the placeholder"
        );
    });

    QUnit.test("image field edition (change size)", async function (assert) {
        assert.expect(10);

        const arch = `
                <form>
                    <sheet>
                        <field name='image' widget='image' options='{"size":[0, 90],"preview_image":"coucou"}'/>
                    </sheet>
                </form>
            `;

        patchWithCleanup(ImageField.prototype, {
            setup() {
                super.setup();
                onMounted(() => {
                    assert.step(
                        `image, width: ${this.props.width}, height: ${this.props.height}, previewImage: ${this.props.previewImage}`
                    );
                });
            },
        });

        await createViewEditor({
            serverData,
            resModel: "partner",
            arch: arch,
            resId: 1,
            type: "form",
            mockRPC: {
                "/web_studio/edit_view": () => {
                    assert.step("edit_view");
                    const newArch = `
                            <form>
                                <sheet>
                                    <field name='image' widget='image' options='{"size":[0, 270],"preview_image":"coucou"}'/>
                                </sheet>
                            </form>
                        `;
                    return createMockViewResult(serverData, "form", newArch, "partner");
                },
            },
        });

        assert.containsOnce(
            target,
            ".o_web_studio_form_view_editor .o_field_image",
            "there should be one image"
        );
        assert.verifySteps(
            ["image, width: undefined, height: 90, previewImage: coucou"],
            "the image should have been fetched"
        );

        // edit the image
        await click(target, ".o_web_studio_form_view_editor .o_field_image", {
            skipVisibilityCheck: true,
        });

        assert.containsOnce(
            target,
            ".o_web_studio_property_size",
            "the sidebar should display dropdown to change image size"
        );

        assert.strictEqual(
            target.querySelector(".o_web_studio_property_size .text-start").textContent,
            "Small",
            "The image size should be correctly selected"
        );
        assert.hasClass(
            target.querySelector(".o_web_studio_form_view_editor .o_field_image"),
            "o-web-studio-editor--element-clicked",
            "image should have the clicked style"
        );

        // change image size to large
        await editAnySelect(
            target,
            ".o_web_studio_sidebar .o_web_studio_property_size .o_select_menu",
            "Large"
        );
        assert.verifySteps(
            ["edit_view", "image, width: undefined, height: 270, previewImage: coucou"],
            "the image should have been fetched again"
        );
        assert.strictEqual(
            target.querySelector(".o_web_studio_property_size .text-start").textContent,
            "Large",
            "The image size should be correctly selected"
        );
    });

    QUnit.test("image size can be unset from the selection", async function (assert) {
        const arch = `<form>
                <sheet>
                    <field name='image' widget='image' class='oe_avatar' options='{"preview_image": "image", "size": [0,90]}'/>
                    <div class='oe_title'>
                        <field name='name'/>
                    </div>
                </sheet>
            </form>`;
        let editViewCount = 0;

        await createViewEditor({
            serverData,
            type: "form",
            resModel: "partner",
            arch: arch,
            mockRPC: function (route, args) {
                if (route === "/web_studio/edit_view") {
                    editViewCount++;
                    let newArch;
                    if (editViewCount === 1) {
                        assert.deepEqual(
                            args.operations[0].new_attrs,
                            {
                                options: '{"preview_image":"image"}',
                            },
                            "size is no longer present in the attrs of the image field"
                        );
                        newArch = `<form>
                                <sheet>
                                    <field name='image' widget='image' class='oe_avatar' options='{"preview_image": "image"}'/>
                                    <div class='oe_title'>
                                        <field name='name'/>
                                    </div>
                                </sheet>
                            </form>`;
                    }
                    return createMockViewResult(serverData, "form", newArch, "partner");
                }
            },
        });

        assert.containsOnce(
            target,
            '.o_field_widget.oe_avatar[name="image"]',
            "there should be avatar image with field image"
        );

        await click(target.querySelector(".o_field_widget[name='image']"));
        assert.strictEqual(
            target.querySelector(".o_web_studio_property_size .o_select_menu").textContent,
            "Small"
        );
        await click(
            target.querySelector(".o_web_studio_property_size .o_select_menu_toggler_clear")
        );
        assert.strictEqual(
            target.querySelector(".o_web_studio_property_size .o_select_menu").textContent,
            ""
        );
    });

    QUnit.test("signature field edition (change full_name)", async function (assert) {
        assert.expect(8);

        const arch = `
                <form>
                    <group>
                        <field name='display_name'/>
                        <field name='m2o'/>
                    </group>
                </form>
            `;

        let editViewCount = 0;
        let newFieldName;

        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch: arch,
            resId: 1,
            mockRPC: function (route, args) {
                if (route === "/web_studio/edit_view") {
                    editViewCount++;
                    let newArch;
                    if (editViewCount === 1) {
                        assert.strictEqual(
                            args.operations[0].node.attrs.widget,
                            "signature",
                            "'signature' widget should be there on field being dropped"
                        );
                        newFieldName = args.operations[0].node.field_description.name;
                        newArch =
                            "<form>" +
                            "<group>" +
                            "<field name='display_name'/>" +
                            "<field name='m2o'/>" +
                            "<field name='" +
                            newFieldName +
                            "' widget='signature'/>" +
                            "</group>" +
                            "</form>";
                        serverData.models.coucou.fields[newFieldName] = {
                            string: "Signature",
                            type: "binary",
                        };
                    } else if (editViewCount === 2) {
                        assert.strictEqual(
                            args.operations[1].new_attrs.options,
                            '{"full_name":"display_name"}',
                            "correct options for 'signature' widget should be passed"
                        );
                        newArch =
                            "<form>" +
                            "<group>" +
                            "<field name='display_name'/>" +
                            "<field name='m2o'/>" +
                            "<field name='" +
                            newFieldName +
                            "' widget='signature' options='{\"full_name\": \"display_name\"}'/>" +
                            "</group>" +
                            "</form>";
                    } else if (editViewCount === 3) {
                        assert.strictEqual(
                            args.operations[2].new_attrs.options,
                            '{"full_name":"m2o"}',
                            "correct options for 'signature' widget should be passed"
                        );
                        newArch =
                            "<form>" +
                            "<group>" +
                            "<field name='display_name'/>" +
                            "<field name='m2o'/>" +
                            "<field name='" +
                            newFieldName +
                            "' widget='signature' options='{\"full_name\": \"m2o\"}'/>" +
                            "</group>" +
                            "</form>";
                    }
                    return createMockViewResult(serverData, "form", newArch, "coucou");
                }
            },
        });

        // drag and drop the new signature field
        disableHookAnimation(target);
        await dragAndDrop(
            ".o_web_studio_new_fields .o_web_studio_field_signature",
            ".o_inner_group .o_web_studio_hook:first-child"
        );

        assert.containsOnce(
            target,
            ".o_web_studio_form_view_editor .o_signature",
            "there should be one signature field"
        );

        // edit the signature
        await click(target.querySelector(".o_web_studio_form_view_editor .o_signature"));

        assert.containsOnce(
            target,
            ".o_web_studio_property_full_name .o-dropdown",
            "the sidebar should display dropdown to change 'Auto-complete with' field"
        );
        assert.strictEqual(
            target.querySelector(".o_web_studio_property_full_name button").textContent,
            "",
            "the auto complete field should be empty by default"
        );

        await editAnySelect(target, ".o_web_studio_property_full_name .o_select_menu", "Name");

        assert.strictEqual(
            target.querySelector(".o_web_studio_property_full_name button").textContent,
            "Name",
            "the auto complete field should be correctly selected"
        );

        // change auto complete field to 'm2o'
        await editAnySelect(target, ".o_web_studio_property_full_name .o_select_menu", "Product");

        assert.strictEqual(
            target.querySelector(".o_web_studio_property_full_name button").textContent,
            "Product",
            "the auto complete field should be correctly selected"
        );
    });

    QUnit.test("integer field should come with 0 as default value", async function (assert) {
        // The arch has a full blown group because the formEditor prevents dropping new Integer fields in a simpler arch
        const arch = `
                <form>
                    <group>
                        <field name='display_name'/>
                    </group>
                </form>`;
        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch: arch,
            mockRPC: (route, args) => {
                if (route === "/web_studio/edit_view") {
                    assert.step("edit_view");
                    assert.strictEqual(args.operations[0].node.field_description.type, "integer");
                    assert.strictEqual(
                        args.operations[0].node.field_description.default_value,
                        "0"
                    );
                }
            },
        });

        disableHookAnimation(target);
        await dragAndDrop(
            target.querySelector(".o_web_studio_new_fields .o_web_studio_field_integer"),
            target.querySelector(".o_web_studio_hook")
        );
        assert.verifySteps(["edit_view"]);
    });

    QUnit.test("invisible form editor", async function (assert) {
        assert.expect(6);

        const arch = `
                <form>
                    <sheet>
                        <field name='display_name' invisible='1'/>
                        <group>
                            <field name='m2o' invisible="id != 42"/>
                        </group>
                    </sheet>
                </form>
            `;

        await createViewEditor({
            type: "form",
            serverData,
            resModel: "coucou",
            arch,
        });

        serverData.views = {
            "coucou,false,form": arch,
        };

        assert.containsNone(target, ".o_web_studio_form_view_editor .o_field_widget");
        assert.containsOnce(
            target,
            ".o_web_studio_form_view_editor .o-web-studio-editor--element-clickable",
            "the invisible node should not be editable (only the group has a node-id set)"
        );
        assert.containsN(
            target,
            ".o_web_studio_form_view_editor .o_web_studio_hook",
            2,
            "there should be two hooks (outside and inside the group"
        );

        // click on show invisible
        await click(target, ".o_web_studio_sidebar li:nth-child(2) a");
        await nextTick();
        await click(target, ".o_web_studio_sidebar input#show_invisible");
        await nextTick();

        assert.containsN(
            target,
            ".o_web_studio_form_view_editor .o_web_studio_show_invisible",
            2,
            "there should be one visible nodes (the invisible ones)"
        );
        assert.containsNone(
            target,
            ".o_web_studio_form_view_editor .o_invisible_modifier",
            "there should be no invisible node"
        );
        assert.containsN(
            target,
            ".o_web_studio_form_view_editor .o_web_studio_hook",
            3,
            "there should be three hooks"
        );
    });

    QUnit.test("form editor - chatter edition", async function (assert) {
        const pyEnv = await startServer();
        serverData.models = {
            ...serverData.models,
            ...pyEnv.getData(),
        };
        setupManager.setupServiceRegistries();

        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch: `
                    <form>
                        <sheet>
                            <field name='display_name'/>
                        </sheet>
                        <div class='oe_chatter'/>
                    </form>
                `,
            mockRPC: {
                "/web_studio/get_email_alias": () => Promise.resolve({ email_alias: "coucou" }),
            },
        });

        await contains(".o_web_studio_form_view_editor .o-mail-Form-chatter");

        // click on the chatter
        await asyncClick(
            ".o_web_studio_form_view_editor .o-mail-Form-chatter .o_web_studio_overlay"
        );
        await nextTick();

        assert.strictEqual(
            currentSidebarTab(),
            "Properties",
            "the Properties tab should now be active"
        );

        await contains('.o_web_studio_sidebar input[name="email_alias"]');
        assert.strictEqual(
            target.querySelector('.o_web_studio_sidebar input[name="email_alias"]').value,
            "coucou",
            "the email alias in sidebar should be fetched"
        );
        assert.hasClass(
            target.querySelector(".o_web_studio_form_view_editor .o-mail-Form-chatter"),
            "o-web-studio-editor--element-clicked",
            "the chatter should have the clicked style"
        );
    });

    QUnit.test(
        "fields without value and label (outside of groups) are shown in form",
        async function (assert) {
            assert.expect(6);

            await createViewEditor({
                serverData,
                resModel: "coucou",
                type: "form",
                arch: `
                        <form>
                            <sheet>
                                <group>
                                    <field name='id'/>
                                    <field name='m2o'/>
                                </group>
                                <field name='display_name'/>
                                <field name='char_field'/>
                            </sheet>
                        </form>
                    `,
                resId: 2,
                mockRPC: {},
            });

            assert.doesNotHaveClass(
                target.querySelector('.o_web_studio_form_view_editor [name="id"]'),
                "o_web_studio_widget_empty",
                "the id field should not have the widget empty class"
            );
            assert.doesNotHaveClass(
                target.querySelector('.o_web_studio_form_view_editor [name="m2o"]'),
                "o_web_studio_widget_empty",
                "the m2o field should not have the widget_empty class"
            );

            assert.hasClass(
                target.querySelector('.o_web_studio_form_view_editor [name="m2o"]'),
                "o_field_empty",
                "the m2o field is empty and therefore should have the o_field_empty class"
            );
            assert.doesNotHaveClass(
                target.querySelector('.o_web_studio_form_view_editor [name="display_name"]'),
                "o_web_studio_widget_empty",
                "the display_name field should not have the o_web_studio_widget_empty class"
            );

            assert.hasClass(
                target.querySelector('.o_web_studio_form_view_editor [name="char_field"]'),
                "o_web_studio_widget_empty",
                "the char_field should have the o_web_studio_widget_empty class"
            );
            assert.strictEqual(
                target.querySelector('.o_web_studio_form_view_editor [name="char_field"]')
                    .innerText,
                "A char",
                "The text in the empty char field should be 'A char'"
            );
        }
    );

    QUnit.test("invisible group in form sheet", async function (assert) {
        assert.expect(8);

        const arch = `<form>
                <sheet>
                    <group>
                        <group class="kikou" string="Kikou" invisible="True"/>
                        <group class="kikou2" string='Kikou2'/>
                    </group>
                </sheet>
            </form>`;

        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch: `<form>
                        <sheet>
                            <group>
                                <group class="kikou" string='Kikou'/>
                                <group class="kikou2" string='Kikou2'/>
                            </group>
                        </sheet>
                    </form>`,
            mockRPC: {
                "/web_studio/edit_view": (route, args) => {
                    assert.equal(
                        args.operations[0].new_attrs.invisible,
                        "True",
                        'we should send "invisible"'
                    );
                    return createMockViewResult(serverData, "form", arch, "coucou");
                },
            },
        });

        assert.containsN(target, ".o_inner_group", 2, "there should be two groups");

        await click(target, ".o_inner_group:first-child");
        await nextTick();
        assert.containsOnce(
            target,
            ".o_web_studio_property input#invisible",
            "should have invisible checkbox"
        );

        assert.ok(
            target.querySelector(".o_web_studio_sidebar .o_web_studio_property input#invisible")
                .checked === false,
            "invisible checkbox should not be checked"
        );

        await click(target, ".o_web_studio_sidebar .o_web_studio_property input#invisible");
        await nextTick();

        assert.containsN(
            target,
            ".o_inner_group",
            1,
            "there should be one visible group now, kikou group is not rendered"
        );

        assert.containsNone(target, ".o-web-studio-editor--element-clicked");
        assert.hasClass(
            target.querySelectorAll(".o_web_studio_sidebar.o_notebook .nav-item a")[0],
            "active"
        );

        await click(target.querySelector(".o_inner_group.kikou2"));
        await nextTick();

        const groupInput = target.querySelector(
            '.o_web_studio_sidebar .o_web_studio_sidebar_text input[name="string"]'
        );
        assert.strictEqual(groupInput.value, "Kikou2", "the group name in sidebar should be set");
    });

    QUnit.test("correctly display hook in form sheet", async function (assert) {
        assert.expect(11);

        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch: `
                <form>
                    <sheet>
                        <!-- hook here -->
                        <group>
                            <group/>
                            <group/>
                        </group>
                        <!-- hook here -->
                        <group>
                            <group/>
                            <group/>
                        </group>
                        <!-- hook here -->
                    </sheet>
                </form>`,
        });

        const sheetHooksValues = [
            {
                xpath: "/form[1]/sheet[1]",
                position: "inside",
                type: "insideSheet",
            },
            {
                xpath: "/form[1]/sheet[1]/group[1]",
                position: "after",
                type: "afterGroup",
            },
            {
                xpath: "/form[1]/sheet[1]/group[2]",
                position: "after",
                type: "afterGroup",
            },
        ];

        target.querySelectorAll(".o_form_sheet > div.o_web_studio_hook").forEach((hook) => {
            const control = sheetHooksValues.shift();
            assert.deepEqual(control, { ...hook.dataset });
        });

        assert.containsN(
            target,
            ".o_web_studio_form_view_editor .o_form_sheet > div.o_web_studio_hook",
            3,
            "there should be three hooks as children of the sheet"
        );

        const innerGroupsHooksValues = [
            {
                xpath: "/form[1]/sheet[1]/group[1]/group[1]",
                position: "inside",
            },
            {
                xpath: "/form[1]/sheet[1]/group[1]/group[2]",
                position: "inside",
            },
            {
                xpath: "/form[1]/sheet[1]/group[2]/group[1]",
                position: "inside",
            },
            {
                xpath: "/form[1]/sheet[1]/group[2]/group[2]",
                position: "inside",
            },
        ];

        target
            .querySelectorAll(".o_form_sheet .o_inner_group > div.o_web_studio_hook")
            .forEach((hook) => {
                const control = innerGroupsHooksValues.shift();
                assert.deepEqual(control, { ...hook.dataset });
            });

        assert.hasClass(
            target.querySelector(".o_web_studio_form_view_editor .o_form_sheet > div:nth-child(1)"),
            "o_web_studio_hook",
            "first div should be a hook"
        );
        assert.hasClass(
            target.querySelector(".o_web_studio_form_view_editor .o_form_sheet > div:nth-child(3)"),
            "o_web_studio_hook",
            "third div should be a hook"
        );
        assert.hasClass(
            target.querySelector(".o_web_studio_form_view_editor .o_form_sheet > div:nth-child(5)"),
            "o_web_studio_hook",
            "last div should be a hook"
        );
    });

    QUnit.test("correctly display hook below group title", async function (assert) {
        assert.expect(14);

        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch: `
                <form>
                    <sheet>
                        <group>
                            </group>
                            <group string='Kikou2'>
                            </group>
                        <group>
                            <field name='m2o'/>
                        </group>
                        <group string='Kikou'>
                            <field name='id'/>
                        </group>
                    </sheet>
                </form>`,
        });

        // first group (without title, without content)
        const firstGroup = target.querySelector(
            ".o_web_studio_form_view_editor .o_inner_group:nth-child(2)"
        );
        assert.containsOnce(
            firstGroup,
            ".o_web_studio_hook",
            "First group, there should be 1 hook"
        );
        assert.hasClass(
            firstGroup.querySelector(":scope > div:nth-child(1)"),
            "o_web_studio_hook",
            "First group, the first div should be a hook"
        );

        // second group (with title, without content)
        const secondGroup = target.querySelector(
            ".o_web_studio_form_view_editor .o_inner_group:nth-child(3)"
        );
        assert.containsOnce(
            secondGroup,
            ".o_web_studio_hook",
            "Second group, there should be 1 hook"
        );
        assert.strictEqual(
            secondGroup.querySelector(":scope > div:nth-child(1)").innerText.toUpperCase(),
            "KIKOU2",
            "Second group, the first div is the group title"
        );
        assert.hasClass(
            secondGroup.querySelector(":scope > div:nth-child(2)"),
            "o_web_studio_hook",
            "Second group, the second div should be a hook"
        );

        // third group (without title, with content)
        const thirdGroup = target.querySelector(
            ".o_web_studio_form_view_editor .o_inner_group:nth-child(4)"
        );
        assert.containsN(
            thirdGroup,
            ".o_web_studio_hook",
            2,
            "Third group, there should be 2 hooks"
        );
        assert.hasClass(
            thirdGroup.querySelector(":scope > div:nth-child(1)"),
            "o_web_studio_hook",
            "Third group, the first div should be a hook"
        );
        assert.strictEqual(
            thirdGroup.querySelector(":scope > div:nth-child(2)").innerText.toUpperCase(),
            "PRODUCT",
            "Third group, the second div is the field"
        );
        assert.containsOnce(
            thirdGroup,
            "div:nth-child(2) .o_web_studio_hook",
            "Third group, the hook should be placed after the field"
        );

        // last group (with title, with content)
        const lastGroup = target.querySelector(
            ".o_web_studio_form_view_editor .o_inner_group:nth-child(5)"
        );
        assert.containsN(lastGroup, ".o_web_studio_hook", 2, "Last group, there should be 2 hooks");
        assert.strictEqual(
            lastGroup.querySelector(":scope > div:nth-child(1)").innerText.toUpperCase(),
            "KIKOU",
            "Last group, the first div is the group title"
        );
        assert.hasClass(
            lastGroup.querySelector(":scope > div:nth-child(2)"),
            "o_web_studio_hook",
            "Last group, the second div should be a hook"
        );
        assert.strictEqual(
            lastGroup.querySelector(":scope > div:nth-child(3)").innerText.toUpperCase(),
            "ID",
            "Last group, the third div is the field"
        );
        assert.containsOnce(
            lastGroup,
            "div:nth-child(3) > .o_web_studio_hook",
            "Last group, the hook is after the field"
        );
    });

    QUnit.test("correctly display hook at the end of tabs -- empty group", async function (assert) {
        assert.expect(1);

        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch: `<form>
                        <sheet>
                            <notebook>
                                <page string='foo'>
                                <group></group>
                                </page>
                            </notebook>
                        </sheet>
                </form>`,
        });

        const childs = document.querySelector(
            ".o_web_studio_form_view_editor .o_notebook .tab-pane.active"
        ).children;

        assert.strictEqual(
            childs[childs.length - 1].classList.contains("o_web_studio_hook"),
            true,
            "When the page contains only an empty group, last child is a studio hook."
        );
    });

    QUnit.test(
        "correctly display hook at the end of tabs -- multiple groups with content and an empty group",
        async function (assert) {
            assert.expect(1);

            await createViewEditor({
                serverData,
                type: "form",
                resModel: "coucou",
                arch: `<form>
                        <sheet>
                            <notebook>
                                <page string="foo">
                                    <group>
                                        <field name="m2o"/>
                                    </group>
                                    <group>
                                        <field name="id"/>
                                    </group>
                                    <group></group>
                                </page>
                            </notebook>
                        </sheet>
                    </form>`,
            });

            const childs = document.querySelector(
                ".o_web_studio_form_view_editor .o_notebook .tab-pane.active"
            ).children;

            assert.strictEqual(
                childs[childs.length - 1].classList.contains("o_web_studio_hook"),
                true,
                "When the page contains multiple groups with content and an empty group, last child is still a studio hook."
            );
        }
    );

    QUnit.test("notebook page hooks", async (assert) => {
        const arch = `
                    <form>
                        <sheet>
                            <notebook>
                                <page string="field"><field name="display_name" /></page>
                                <page string="outer">
                                    <group><group></group></group>
                                </page>
                                <page string='foo'>
                                    <group>
                                        <field name='m2o'/>
                                    </group>
                                    <group>
                                        <field name='id'/>
                                    </group>
                                    <group></group>
                                </page>
                            </notebook>
                        </sheet>
                    </form>`;

        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch,
        });

        assert.containsOnce(target, ".o_notebook .tab-pane.active > .o_web_studio_hook");

        assert.deepEqual(
            {
                ...target.querySelector(".o_notebook .tab-pane.active > .o_web_studio_hook")
                    .dataset,
            },
            {
                position: "inside",
                type: "page",
                xpath: "/form[1]/sheet[1]/notebook[1]/page[1]",
            }
        );
        await click(target.querySelectorAll(".o_notebook .nav-item a")[4]);
        assert.containsOnce(target, ".o_notebook .tab-pane.active > .o_web_studio_hook");

        assert.deepEqual(
            {
                ...target.querySelector(".o_notebook .tab-pane.active > .o_web_studio_hook")
                    .dataset,
            },
            {
                position: "after",
                type: "afterGroup",
                xpath: "/form[1]/sheet[1]/notebook[1]/page[2]/group[1]",
            }
        );

        await click(target.querySelectorAll(".o_notebook .nav-item a")[5]);
        assert.containsOnce(target, ".o_notebook .tab-pane.active > .o_web_studio_hook");
        assert.deepEqual(
            {
                ...target.querySelector(".o_notebook .tab-pane.active > .o_web_studio_hook")
                    .dataset,
            },
            {
                position: "inside",
                type: "page",
                xpath: "/form[1]/sheet[1]/notebook[1]/page[3]",
            }
        );
    });

    QUnit.test("notebook edition", async function (assert) {
        assert.expect(9);

        const arch = `
                <form>
                    <sheet>
                        <group>
                            <field name='display_name'/>
                        </group>
                        <notebook>
                            <page string='Kikou'>
                                <field name='id'/>
                            </page>
                        </notebook>
                    </sheet>
                </form>`;

        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch: arch,
            mockRPC: function (route, args) {
                if (route === "/web_studio/edit_view") {
                    assert.strictEqual(
                        args.operations[0].node.tag,
                        "page",
                        "a page should be added"
                    );
                    assert.strictEqual(
                        args.operations[0].node.attrs.string,
                        "New Page",
                        "the string attribute should be set"
                    );
                    assert.strictEqual(
                        args.operations[0].position,
                        "inside",
                        "a page should be added inside the notebook"
                    );
                    assert.strictEqual(
                        args.operations[0].target.tag,
                        "notebook",
                        "the target should be the notebook in edit_view"
                    );
                    return createMockViewResult(serverData, "form", arch, "coucou");
                }
            },
        });

        assert.containsN(
            target,
            ".o_content .o_notebook li",
            2,
            "there should be one existing page and a fake one"
        );

        // // click on existing tab
        const firstTab = target.querySelector(".o_content .o_notebook li");
        await click(firstTab);

        assert.hasClass(
            firstTab,
            "o-web-studio-editor--element-clicked",
            "the page should be clickable"
        );

        assert.containsN(
            target,
            ".o_web_studio_property",
            2,
            "the sidebar should now display the page properties"
        );

        assert.strictEqual(
            document.querySelector(".o_web_studio_property.o_web_studio_sidebar_text input").value,
            "Kikou",
            "the page name in sidebar should be set"
        );

        assert.containsOnce(
            target,
            ".o_limit_group_visibility",
            "the groups should be editable for notebook pages"
        );

        // add a new page
        await click(document.querySelectorAll(".o_content .o_notebook li")[1]);
    });

    QUnit.test("notebook with empty page", async (assert) => {
        assert.expect(3);

        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch: `<form>
                        <sheet>
                            <notebook>
                                <page string="field"></page>
                            </notebook>
                        </sheet>
                    </form>`,
        });

        await click(target.querySelector(".o_web_studio_view_renderer .o_notebook li"));
        assert.strictEqual(
            currentSidebarTab(),
            "Properties",
            "The sidebar should now display the properties tab"
        );
        assert.containsN(
            target,
            ".o_web_studio_property",
            2,
            "the sidebar should now display the page properties"
        );
        assert.strictEqual(
            target.querySelectorAll(".o_web_studio_property input")[1].value,
            "field",
            "the page label is correctly set"
        );
    });

    QUnit.test("notebook with empty page and fields inside the element", async (assert) => {
        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch: `<form>
                        <sheet>
                            <notebook>
                                <page string="Page"></page>
                                <field name='id' invisible='1'/>
                                <page string="Empty"></page>
                            </notebook>
                        </sheet>
                    </form>`,
        });

        await click(target.querySelector(".o_web_studio_view_renderer .o_notebook li"));
        assert.strictEqual(
            target.querySelector(".o_form_sheet .o_notebook_headers li:nth-child(2)").dataset
                .studioXpath,
            "/form[1]/sheet[1]/notebook[1]/page[2]"
        );
        await click(target, ".o_form_sheet .o_notebook_headers li:nth-child(2) a", true);
        assert.strictEqual(
            target.querySelectorAll(".o_web_studio_property input")[1].value,
            "Empty",
            "the page label is correctly set"
        );
    });

    QUnit.test("invisible notebook page in form", async function (assert) {
        assert.expect(9);

        const arch = `
            <form>
                <sheet>
                    <notebook>
                        <page class="kikou" string='Kikou' invisible="True">
                            <field name='id'/>
                        </page>
                        <page class="kikou2" string='Kikou2'>
                            <field name='char_field'/>
                        </page>
                    </notebook>
                </sheet>
            </form>`;

        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch: `<form>
                        <sheet>
                            <notebook>
                                <page class="kikou" string='Kikou'>
                                    <field name='id'/>
                                </page>
                                <page class="kikou2" string='Kikou2'>
                                    <field name='char_field'/>
                                </page>
                            </notebook>
                        </sheet>
                    </form>`,
            mockRPC: function (route, args) {
                if (route === "/web_studio/edit_view") {
                    assert.equal(
                        args.operations[0].new_attrs.invisible,
                        "True",
                        'we should send "invisible"'
                    );
                    return createMockViewResult(serverData, "form", arch, "coucou");
                }
            },
        });

        assert.containsN(
            target,
            ".o_web_studio_view_renderer .o_notebook li.o-web-studio-editor--element-clickable",
            2,
            "there should be two pages"
        );

        await click(target.querySelector(".o_web_studio_view_renderer .o_notebook li"));
        assert.containsOnce(
            target,
            ".o_web_studio_sidebar input#invisible",
            "should have invisible checkbox"
        );
        const invisibleCheckbox = target.querySelector(".o_web_studio_sidebar input#invisible");
        assert.strictEqual(
            invisibleCheckbox.checked,
            false,
            "invisible checkbox should not be checked"
        );

        await click(invisibleCheckbox);
        await nextTick();
        assert.containsN(
            target,
            ".o_web_studio_view_renderer .o_notebook li",
            2,
            "there should be one visible page and a fake one"
        );
        assert.isNotVisible(
            target.querySelector(".o_notebook li .kikou"),
            "there should be an invisible page"
        );

        assert.containsNone(target, ".o-web-studio-editor--element-clicked");

        assert.strictEqual(currentSidebarTab(), "Add");

        await click(target.querySelector("li .kikou2"));
        assert.strictEqual(
            target.querySelector(".o_web_studio_property.o_web_studio_sidebar_text input").value,
            "Kikou2",
            "the page name in sidebar should be set"
        );
    });

    QUnit.test(
        "restore active notebook tab after adding/removing an element",
        async function (assert) {
            const arch = `
        <form>
            <sheet>
                <notebook>
                    <page class="kikou" string='Kikou'>
                        <field name='id'/>
                    </page>
                    <page class="kikou2" string='Kikou2'>
                        <field name='char_field'/>
                    </page>
                </notebook>
            </sheet>
        </form>`;

            await createViewEditor({
                serverData,
                type: "form",
                resModel: "coucou",
                arch,
                mockRPC: function (route, args) {
                    if (route === "/web_studio/edit_view") {
                        assert.step("edit_view");
                        return createMockViewResult(serverData, "form", arch, "coucou");
                    }
                },
            });

            await click(target.querySelector(".o_notebook .kikou2"));
            await click(target.querySelector(".nav-link.o_web_studio_new"));

            disableHookAnimation(target);
            await dragAndDrop(
                target.querySelector(".o_web_studio_new_fields .o_web_studio_field_integer"),
                target.querySelector(".o_notebook_content .o_web_studio_hook")
            );
            await notebookRestoreElement();
            assert.verifySteps(["edit_view"]);
            assert.hasClass(
                target.querySelector(".kikou2"),
                "active",
                "second notebook page is still active"
            );
            assert.strictEqual(
                currentSidebarTab(),
                "Add",
                "the Add tab should still be active after adding an element"
            );

            await click(target.querySelector("div[name=char_field]"));
            assert.hasClass(
                target.querySelector("div[name=char_field]"),
                "o-web-studio-editor--element-clicked",
                "field element is selected"
            );

            await click(target.querySelector(".o_web_studio_remove"));
            await click(target.querySelector(".modal .btn-primary"));
            assert.hasClass(
                target.querySelector(".kikou2"),
                "active",
                "second notebook page is still active"
            );
            assert.strictEqual(
                currentSidebarTab(),
                "Add",
                "the Add tab should still be active after adding an element"
            );
            assert.verifySteps(["edit_view"]);
        }
    );

    QUnit.test("restore active notebook tab and element", async function (assert) {
        const arch = `
        <form>
            <sheet>
                <notebook>
                    <page class="kikou" string='Kikou'>
                        <field name='id'/>
                    </page>
                    <page class="kikou2" string='Kikou2'>
                        <field name='char_field'/>
                    </page>
                </notebook>
            </sheet>
        </form>`;

        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch,
            mockRPC: function (route, args) {
                if (route === "/web_studio/edit_view") {
                    assert.step("value has been edited");
                    return createMockViewResult(serverData, "form", arch, "coucou");
                }
            },
        });

        // first, let's change the properties of a tab element
        await click(target.querySelector(".o_notebook .kikou2"));
        await editInput(target.querySelector("input[name=string]"), null, "Kikou deux");
        await notebookRestoreElement();
        assert.verifySteps(["value has been edited"]);
        assert.hasClass(
            target.querySelector(".o_form_sheet .nav-item:nth-child(2)"),
            "o-web-studio-editor--element-clicked",
            "second tab is selected"
        );

        // verify that the second tab does not keep the highlight when selecting another tab
        await click(target.querySelector(".o_notebook .kikou"));
        await notebookRestoreElement();
        assert.hasClass(
            target.querySelector(".o_form_sheet .nav-item:nth-child(1)"),
            "o-web-studio-editor--element-clicked",
            "first tab is now selected"
        );

        // now let's change the properties of an inside element
        await click(target.querySelector(".o_notebook .kikou2"));
        await click(target.querySelector("div[name=char_field]"));
        assert.hasClass(
            target.querySelector("div[name=char_field]"),
            "o-web-studio-editor--element-clicked",
            "field element is selected"
        );
        assert.strictEqual(
            currentSidebarTab(),
            "Properties",
            "the Properties tab for the selected element should now be active"
        );

        await editInput(target.querySelector("input[name=placeholder]"), null, "ae");
        await notebookRestoreElement();
        assert.hasClass(
            target.querySelector("div[name=char_field]"),
            "o-web-studio-editor--element-clicked",
            "field element is selected"
        );
        assert.strictEqual(
            currentSidebarTab(),
            "Properties",
            "the Properties tab for the selected element is still active"
        );
        assert.verifySteps(["value has been edited"]);
    });

    QUnit.test("restore active notebook tab after view property change", async function (assert) {
        const arch = `
        <form>
            <sheet>
                <notebook>
                    <page class="kikou" string='Kikou'>
                        <field name='id'/>
                    </page>
                    <page class="kikou2" string='Kikou2'>
                        <field name='char_field'/>
                    </page>
                </notebook>
            </sheet>
        </form>`;

        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch,
            mockRPC: function (route, args) {
                if (route === "/web_studio/edit_view") {
                    assert.step("value has been edited");
                    return createMockViewResult(serverData, "form", arch, "coucou");
                }
            },
        });

        await click(target.querySelector(".o_notebook .kikou2"));
        assert.hasClass(
            target.querySelector(".kikou2"),
            "active",
            "second notebook page is still active"
        );

        await click(target.querySelector(".nav-link.o_web_studio_view"));
        assert.strictEqual(currentSidebarTab(), "View", "the View tab is now active");

        await click(target.querySelector("input[name=edit]"));
        await notebookRestoreElement();
        assert.verifySteps(["value has been edited"]);
        assert.strictEqual(
            currentSidebarTab(),
            "View",
            "the View tab for the selected element is still active"
        );
        assert.hasClass(
            target.querySelector(".kikou2"),
            "active",
            "second notebook page is still active"
        );
    });

    QUnit.test("label edition", async function (assert) {
        assert.expect(10);

        const arch = `
            <form>
                <sheet>
                    <group>
                        <label for='display_name' string='Kikou'/>
                        <div><field name='display_name' nolabel='1'/></div>
                        <field name="char_field"/>
                    </group>
                </sheet>
            </form>`;
        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch: arch,
            mockRPC: function (route, args) {
                if (route === "/web_studio/edit_view") {
                    assert.deepEqual(
                        args.operations[0].target,
                        {
                            tag: "label",
                            attrs: {
                                for: "display_name",
                            },
                            xpath_info: [
                                {
                                    indice: 1,
                                    tag: "form",
                                },
                                {
                                    indice: 1,
                                    tag: "sheet",
                                },
                                {
                                    indice: 1,
                                    tag: "group",
                                },
                                {
                                    indice: 1,
                                    tag: "label",
                                },
                            ],
                        },
                        "the target should be set in edit_view"
                    );
                    assert.deepEqual(
                        args.operations[0].new_attrs,
                        { string: "Yeah" },
                        "the string attribute should be set in edit_view"
                    );
                    return createMockViewResult(serverData, "form", arch, "coucou");
                }
            },
        });

        const label = document.querySelector(".o_web_studio_form_view_editor label");
        assert.strictEqual(label.innerText, "Kikou", "the label should be correctly set");
        await click(label);

        assert.hasClass(
            label,
            "o-web-studio-editor--element-clicked",
            "the label should be clicked"
        );

        assert.containsOnce(
            target,
            ".o_web_studio_property",
            "the sidebar should now display the label properties"
        );

        const sidebarlabel = document.querySelector(".o_web_studio_sidebar_text input");
        assert.strictEqual(sidebarlabel.value, "Kikou", "the label name in sidebar should be set");

        editInput(document, ".o_web_studio_sidebar_text input", "Yeah");

        const charFieldLabel = document.querySelectorAll("label.o_form_label")[1];
        assert.strictEqual(
            charFieldLabel.innerText,
            "A char",
            "The second label should be 'A char'"
        );

        await click(charFieldLabel);

        assert.doesNotHaveClass(
            label,
            "o-web-studio-editor--element-clicked",
            "the field label should not be clicked"
        );

        assert.containsN(
            target,
            ".o_web_studio_property",
            9,
            "the sidebar should now display the field properties"
        );

        const charFieldSidebarLabel = document.querySelector(".o_web_studio_sidebar_text input");
        assert.strictEqual(
            charFieldSidebarLabel.value,
            "A char",
            "the label name in sidebar should be set"
        );
    });

    QUnit.test("add a statusbar", async function (assert) {
        assert.expect(8);

        const arch = `
            <form>
                <sheet>
                    <group><field name='display_name'/></group>
                </sheet>
            </form>`;

        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch: arch,
            mockRPC(route, args) {
                if (route === "/web_studio/edit_view") {
                    assert.strictEqual(
                        args.operations.length,
                        2,
                        "there should be 2 operations (one for statusbar and one for the new field"
                    );
                    assert.deepEqual(args.operations[0], { type: "statusbar" });
                    assert.deepEqual(
                        args.operations[1].target,
                        { tag: "header" },
                        "the target should be correctly set"
                    );
                    assert.strictEqual(
                        args.operations[1].position,
                        "inside",
                        "the position should be correctly set"
                    );
                    assert.deepEqual(
                        args.operations[1].node.attrs,
                        { widget: "statusbar", options: "{'clickable': '1'}" },
                        "the options should be correctly set"
                    );
                }
            },
        });

        const statusbar = target.querySelector(
            ".o_web_studio_form_view_editor .o_web_studio_statusbar_hook"
        );
        assert.containsOnce(
            target,
            ".o_web_studio_form_view_editor .o_web_studio_statusbar_hook",
            "there should be a hook to add a statusbar"
        );

        await click(statusbar);
        assert.containsOnce(target, ".o_dialog .modal", "there should be one modal");
        assert.containsN(
            target,
            ".o_dialog .o_web_studio_selection_editor li.o-draggable .o-web-studio-interactive-list-item-label",
            3,
            "there should be 3 pre-filled values for the selection field"
        );
        await click(target.querySelector(".modal-footer .btn-primary"));
    });

    QUnit.test("move a field in form", async function (assert) {
        assert.expect(3);
        const arch = `<form>
                <sheet>
                    <group>
                        <field name='display_name'/>
                        <field name='char_field'/>
                        <field name='m2o'/>
                    </group>
                </sheet>
            </form>`;

        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch: arch,
            mockRPC: function (route, args) {
                if (route === "/web_studio/edit_view") {
                    assert.deepEqual(
                        args.operations[0],
                        {
                            node: {
                                tag: "field",
                                attrs: { name: "m2o" },
                                xpath_info: [
                                    {
                                        indice: 1,
                                        tag: "form",
                                    },
                                    {
                                        indice: 1,
                                        tag: "sheet",
                                    },
                                    {
                                        indice: 1,
                                        tag: "group",
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
                                xpath_info: [
                                    {
                                        indice: 1,
                                        tag: "form",
                                    },
                                    {
                                        indice: 1,
                                        tag: "sheet",
                                    },
                                    {
                                        indice: 1,
                                        tag: "group",
                                    },
                                    {
                                        indice: 1,
                                        tag: "field",
                                    },
                                ],
                                attrs: { name: "display_name" },
                            },
                            type: "move",
                        },
                        "the move operation should be correct"
                    );
                    // the server sends the arch in string but it's post-processed
                    // by the ViewEditorManager
                    const arch =
                        "<form>" +
                        "<sheet>" +
                        "<group>" +
                        "<field name='m2o'/>" +
                        "<field name='display_name'/>" +
                        "<field name='char_field'/>" +
                        "</group>" +
                        "</sheet>" +
                        "</form>";
                    return createMockViewResult(serverData, "form", arch, "coucou");
                }
            },
        });

        assert.strictEqual(
            target.querySelector(".o_web_studio_form_view_editor .o_form_sheet").innerText,
            "Name\nA char\nProduct",
            "The initial ordering of the fields must be correct"
        );

        // Don't be bothered by transition effects
        disableHookAnimation(target);
        // move m2o before display_name
        await dragAndDrop(
            ".o-draggable[data-field-name='m2o']",
            ".o_inner_group .o_web_studio_hook"
        );
        assert.strictEqual(
            target.querySelector(".o_web_studio_form_view_editor .o_form_sheet").innerText,
            "Product\nName\nA char",
            "The ordering of the fields after the dragAndDrop should be correct"
        );
    });

    QUnit.test("form editor add avatar image", async function (assert) {
        assert.expect(15);
        const arch = `<form>
                <sheet>
                    <div class='oe_title'>
                        <field name='name'/>
                    </div>
                </sheet>
            </form>`;
        let editViewCount = 0;

        await createViewEditor({
            serverData,
            type: "form",
            resModel: "partner",
            arch: arch,
            mockRPC: function (route, args) {
                if (route === "/web_studio/edit_view") {
                    editViewCount++;
                    let newArch;
                    if (editViewCount === 1) {
                        assert.deepEqual(
                            args.operations[0],
                            {
                                field: "image",
                                type: "avatar_image",
                            },
                            "Proper field name and operation type should be passed"
                        );
                        newArch = `<form>
                                <sheet>
                                    <field name='image' widget='image' class='oe_avatar' options='{"preview_image": "image"}'/>
                                    <div class='oe_title'>
                                        <field name='name'/>
                                    </div>
                                </sheet>
                            </form>`;
                    } else if (editViewCount === 2) {
                        assert.deepEqual(
                            args.operations[1],
                            {
                                type: "remove",
                                target: {
                                    tag: "field",
                                    attrs: {
                                        name: "image",
                                        class: "oe_avatar",
                                    },
                                    xpath_info: [
                                        {
                                            indice: 1,
                                            tag: "form",
                                        },
                                        {
                                            indice: 1,
                                            tag: "sheet",
                                        },
                                        {
                                            indice: 1,
                                            tag: "field",
                                        },
                                    ],
                                },
                            },
                            "Proper field name and operation type should be passed"
                        );
                        newArch = arch;
                    } else if (editViewCount === 3) {
                        assert.deepEqual(
                            args.operations[2],
                            {
                                field: "",
                                type: "avatar_image",
                            },
                            "Proper field name and operation type should be passed"
                        );
                        serverData.models.partner.fields["x_avatar_image"] = {
                            string: "Image",
                            type: "binary",
                        };
                        newArch = `<form>
                                <sheet>
                                    <field name='x_avatar_image' widget='image' class='oe_avatar' options='{"preview_image": "x_avatar_image"}'/>
                                    <div class='oe_title'>
                                        <field name='name'/>
                                    </div>
                                </sheet>
                            </form>`;
                    }
                    //serverData, arch, model
                    return createMockViewResult(serverData, "form", newArch, "partner");
                }
            },
        });

        assert.containsNone(
            target,
            ".o_field_widget.oe_avatar",
            "there should be no avatar image field"
        );

        assert.containsOnce(
            target,
            ".oe_avatar.o_web_studio_avatar",
            "there should be the hook for avatar image"
        );

        // Test with existing field.
        await click(target.querySelector(".oe_avatar.o_web_studio_avatar"));
        await nextTick();

        assert.containsN(
            target,
            ".modal .modal-body select > option",
            3,
            "there should be three option Field selection drop-down "
        );

        assert.containsOnce(
            target,
            ".modal .modal-body select > option[value='image']",
            "there should be 'Image' option with proper value set in Field selection drop-down"
        );

        // add existing image field
        await editAnySelect(target, "select[name='field']", "image");

        // Click 'Confirm' Button
        await click(target.querySelector(".modal .modal-footer .btn-primary"));
        assert.containsOnce(
            target,
            '.o_field_widget.oe_avatar[name="image"]',
            "there should be avatar image with field image"
        );
        assert.containsNone(
            target,
            ".oe_avatar.o_web_studio_avatar",
            "the avatar image hook should not be there"
        );

        // Remove already added field from view to test new image field case.
        await click(target.querySelector(".oe_avatar"));
        await click(target.querySelector(".o_web_studio_sidebar .o_web_studio_remove"));
        assert.strictEqual(
            target.querySelector(".modal-body").innerText,
            "Are you sure you want to remove this field from the view?",
            "dialog should display the correct message"
        );
        await click(target.querySelector(".modal-footer .btn-primary"));
        assert.containsNone(
            target,
            ".o_field_widget.oe_avatar",
            "there should be no avatar image field"
        );
        assert.containsOnce(
            target,
            ".oe_avatar.o_web_studio_avatar",
            "there should be the hook for avatar image"
        );

        // Test with new field.
        await click(target.querySelector(".oe_avatar.o_web_studio_avatar"));
        assert.containsOnce(
            target,
            ".modal .modal-body select > option.o_new",
            "there should be 'New Field' option in Field selection drop-down"
        );
        // add new image field
        await editAnySelect(target, "select[name='field']", "");
        // Click 'Confirm' Button
        await click(target.querySelector(".modal .modal-footer .btn-primary"));
        assert.containsOnce(
            target,
            '.o_field_widget.oe_avatar[name="x_avatar_image"]',
            "there should be avatar image with field name x_avatar_image"
        );
        assert.containsNone(
            target,
            ".oe_avatar.o_web_studio_avatar",
            "there should be no hook for avatar image"
        );
    });

    QUnit.test("sidebar for a related field", async function (assert) {
        serverData.models.product.fields.related = {
            type: "char",
            related: "partner.display_name",
            string: "myRelatedField",
        };
        const arch = `<form>
                <sheet>
                    <div class='oe_title'>
                        <field name='related'/>
                    </div>
                </sheet>
            </form>`;

        await createViewEditor({
            serverData,
            type: "form",
            resModel: "product",
            arch: arch,
        });

        const fieldTarget = target.querySelector(".o_field_widget[name='related']");
        assert.hasClass(fieldTarget, "o_web_studio_widget_empty");
        assert.strictEqual(fieldTarget.textContent, "myRelatedField");
        await click(fieldTarget);
        assert.strictEqual(
            target.querySelector(".o_web_studio_sidebar .nav-link.active").textContent,
            "Properties"
        );
        assert.strictEqual(target.querySelector("input[name='string']").value, "myRelatedField");
    });

    QUnit.test("Phone field in form with SMS", async function (assert) {
        serverData.models.coucou.fields.display_name.string = "Display Name";
        const arch = `
        <form><sheet>
            <group>
                <field name='display_name' widget='phone' />
            </group>
        </sheet></form>`;
        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch: arch,
            mockRPC(route, args) {
                if (route === "/web_studio/edit_view") {
                    assert.step("edit_view");
                    assert.deepEqual(args.operations[0].node.attrs, {
                        name: "display_name",
                        widget: "phone",
                    });
                    assert.deepEqual(args.operations[0].new_attrs, {
                        options: '{"enable_sms":false}',
                    });
                }
            },
        });

        await click(selectorContains(target, ".o_form_label", "Display Name"));
        assert.containsOnce(
            target,
            '.o_web_studio_sidebar input[id="enable_sms"]:checked',
            "By default the boolean should be true"
        );
        await click(target.querySelector('.o_web_studio_sidebar input[id="enable_sms"]'));
        assert.verifySteps(["edit_view"]);
    });

    QUnit.test("modification of field appearing multiple times in view", async function (assert) {
        // the typical case of the same field in a single view is conditional sub-views
        // that use invisible="py expression"
        // if the targeted node is after a hidden view, the hidden one should be ignored / skipped
        const arch = `<form>
            <group invisible="1">
                <field name="display_name"/>
            </group>
            <group>
                <field name="display_name"/>
            </group>
            <group>
                <field name="char_field" />
            </group>
        </form>`;

        await createViewEditor({
            serverData,
            type: "form",
            arch: arch,
            resModel: "coucou",
            mockRPC: function (route, args) {
                if (route === "/web_studio/edit_view") {
                    assert.step("edit_view");
                    assert.deepEqual(
                        args.operations[0].target.xpath_info,
                        [
                            {
                                tag: "form",
                                indice: 1,
                            },
                            {
                                tag: "group",
                                indice: 2,
                            },
                            {
                                tag: "field",
                                indice: 1,
                            },
                        ],
                        "the target should be the field of the second group"
                    );
                    assert.deepEqual(
                        args.operations[0].new_attrs,
                        { string: "Foo" },
                        "the string attribute should be changed from default to 'Foo'"
                    );
                }
            },
        });

        const visibleElement = target.querySelector(
            ".o_web_studio_form_view_editor .o_wrap_label.o-web-studio-editor--element-clickable"
        );
        assert.strictEqual(visibleElement.textContent, "Name", "the name should be correctly set");

        await click(visibleElement);
        const labelInput = target.querySelector('.o_web_studio_property input[name="string"]');
        assert.strictEqual(labelInput.value, "Name", "the name in the sidebar should be set");
        await editInput(labelInput, null, "Foo");
        assert.verifySteps(["edit_view"]);
    });

    QUnit.test("Open form view with button_box in studio", async function (assert) {
        assert.expect(1);

        const arch = `<form>
            <div name="button_box" class="oe_button_box" invisible="not display_name">
                <button type="object" class="oe_stat_button" icon="fa-check-square">
                    <field name="display_name"/>
                </button>
            </div>
        </form>`;
        await createViewEditor({
            serverData,
            type: "form",
            arch: arch,
            resModel: "partner",
            resId: 1,
        });

        const buttonBoxFieldEl = target.querySelector(
            ".o-form-buttonbox button .o_field_widget span"
        );
        assert.strictEqual(buttonBoxFieldEl.textContent, "jean", "there should be a button_box");
    });

    QUnit.test("new button in buttonbox", async function (assert) {
        assert.expect(6);
        patchWithCleanup(browser, { setTimeout: () => 1 });
        const arch = `<form><sheet><field name='display_name'/></sheet></form>`;
        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch,
            mockRPC(route, args) {
                if (args.method === "name_search") {
                    return [[1, "Test Field (Test)"]];
                }
                if (route === "/web_studio/edit_view") {
                    assert.deepEqual(args.operations, [
                        { type: "buttonbox" },
                        {
                            type: "add",
                            target: {
                                tag: "div",
                                attrs: {
                                    class: "oe_button_box",
                                },
                            },
                            position: "inside",
                            node: {
                                tag: "button",
                                field: 1,
                                string: "New button",
                                attrs: {
                                    class: "oe_stat_button",
                                    icon: "fa-diamond",
                                },
                            },
                        },
                    ]);
                    return createMockViewResult(serverData, "form", arch, "partner");
                }
            },
        });

        await click(target.querySelector(".o_web_studio_button_hook"));
        assert.containsOnce(target, ".o_dialog .modal", "there should be one modal");
        assert.containsOnce(
            target,
            ".o_dialog .o_input_dropdown .o-autocomplete",
            "there should be a many2one for the related field"
        );
        await click(target.querySelector(".modal-footer button:first-child"));
        assert.containsOnce(
            target,
            ".o_notification",
            "notification shown at confirm when no field selected"
        );
        assert.containsOnce(target, ".o_dialog .modal", "dialog is still present");

        await click(target.querySelector(".o-autocomplete--input"));
        await click(target.querySelector(".o-autocomplete .o-autocomplete--dropdown-item"));
        await click(target.querySelector(".modal-footer button:first-child"));
        assert.containsNone(target, ".o_dialog .modal", "should not display the create modal");
    });

    QUnit.test("new button in buttonbox through 'Search more'", async function (assert) {
        patchWithCleanup(browser, { setTimeout: () => 1 });
        const arch = `<form><sheet><field name='display_name'/></sheet></form>`;
        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch,
            mockRPC(route, args) {
                if (args.method === "name_search") {
                    return [
                        [1, "Test Field (Test)"],
                        [2, "Test Field (Test)"],
                        [3, "Test Field (Test)"],
                        [4, "Test Field (Test)"],
                        [5, "Test Field (Test)"],
                        [6, "Test Field (Test)"],
                        [7, "Test Field (Test)"],
                        [8, "Test Field (Test)"],
                    ];
                }
                if (route === "/web_studio/edit_view") {
                    assert.deepEqual(args.operations, [
                        { type: "buttonbox" },
                        {
                            type: "add",
                            target: {
                                tag: "div",
                                attrs: {
                                    class: "oe_button_box",
                                },
                            },
                            position: "inside",
                            node: {
                                tag: "button",
                                field: 1,
                                string: "New button",
                                attrs: {
                                    class: "oe_stat_button",
                                    icon: "fa-diamond",
                                },
                            },
                        },
                    ]);
                    return createMockViewResult(serverData, "form", arch, "partner");
                }
            },
        });

        await click(target.querySelector(".o_web_studio_button_hook"));
        assert.containsOnce(target, ".o_dialog .modal", "there should be one modal");
        assert.containsOnce(
            target,
            ".o_dialog .o_input_dropdown .o-autocomplete",
            "there should be a many2one for the related field"
        );
        await click(target.querySelector(".modal-footer button:first-child"));
        assert.containsOnce(
            target,
            ".o_notification",
            "notification shown at confirm when no field selected"
        );
        assert.containsOnce(target, ".o_dialog .modal", "dialog is still present");

        await click(target.querySelector(".o-autocomplete--input"));
        await click(target.querySelector(".o_m2o_dropdown_option_search_more"));
        await click(target.querySelector(".o_list_view .o_data_row .o_data_cell"));
        assert.strictEqual(target.querySelector(".o-autocomplete--input").value, "Select me");
        await click(target.querySelector(".modal-footer button:first-child"));
        assert.containsNone(target, ".o_dialog .modal", "should not display the create modal");
    });

    QUnit.test("buttonbox with invisible button, then show invisible", async function (assert) {
        serverData.models["coucou"].records[0] = {
            display_name: "someName",
            id: 99,
        };

        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch: `
                <form>
                    <sheet>
                        <div class="oe_button_box" name="button_box">
                            <button name="someName" class="someClass" type="object"
                                invisible="display_name == &quot;someName&quot;" />
                        </div>
                        <field name='display_name'/>
                    </sheet>
                </form>`,
            resId: 99,
        });
        assert.containsOnce(target, ".o-form-buttonbox .o_web_studio_button_hook");
        assert.containsNone(target, "button.someClass");

        await click(selectorContains(target, ".o_web_studio_sidebar .nav-link", "View"));
        await click(target.querySelector(".o_web_studio_sidebar #show_invisible"));

        assert.containsOnce(target, "button.someClass");
    });

    QUnit.test("element removal", async function (assert) {
        assert.expect(10);

        let editViewCount = 0;
        const arch = `<form><sheet>
                    <group>
                        <field name='display_name'/>
                        <field name='m2o'/>
                    </group>
                    <notebook><page name='page'><field name='id'/></page></notebook>
                </sheet></form>`;
        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch: arch,
            mockRPC(route, args) {
                if (route === "/web_studio/edit_view") {
                    editViewCount++;
                    if (editViewCount === 1) {
                        assert.strictEqual(
                            Object.prototype.hasOwnProperty.call(
                                args.operations[0].target,
                                "xpath_info"
                            ),
                            true,
                            "should give xpath_info even if we have the tag identifier attributes"
                        );
                    } else if (editViewCount === 2) {
                        assert.strictEqual(
                            Object.prototype.hasOwnProperty.call(
                                args.operations[1].target,
                                "xpath_info"
                            ),
                            true,
                            "should give xpath_info even if we have the tag identifier attributes"
                        );
                    } else if (editViewCount === 3) {
                        assert.strictEqual(
                            args.operations[2].target.tag,
                            "group",
                            "should compute correctly the parent node for the group"
                        );
                    } else if (editViewCount === 4) {
                        assert.strictEqual(
                            args.operations[3].target.tag,
                            "notebook",
                            "should delete the notebook because the last page is deleted"
                        );
                        assert.strictEqual(
                            args.operations[3].target.xpath_info.at(-1).tag,
                            "notebook",
                            "should have the notebook as xpath last element"
                        );
                    }
                    return createMockViewResult(serverData, "form", arch, "coucou");
                }
            },
        });
        // remove field
        await click(target.querySelector('[name="display_name"]').parentElement);
        await click(target.querySelector(".o_web_studio_sidebar .o_web_studio_remove"));
        assert.strictEqual(
            target.querySelector(".modal-body").textContent,
            "Are you sure you want to remove this field from the view?",
            "should display the correct message"
        );
        await click(target.querySelector(".modal .btn-primary"));

        // remove other field so group is empty
        await click(target.querySelector('[name="m2o"]').parentElement);
        await click(target.querySelector(".o_web_studio_sidebar .o_web_studio_remove"));
        assert.strictEqual(
            target.querySelector(".modal-body").textContent,
            "Are you sure you want to remove this field from the view?",
            "should display the correct message"
        );
        await click(target.querySelector(".modal .btn-primary"));

        // remove group
        await click(target.querySelector(".o_inner_group.o-web-studio-editor--element-clickable"));
        await click(target.querySelector(".o_web_studio_sidebar .o_web_studio_remove"));
        assert.strictEqual(
            target.querySelector(".modal-body").textContent,
            "Are you sure you want to remove this group from the view?",
            "should display the correct message"
        );
        await click(target.querySelector(".modal .btn-primary"));

        // remove page
        await click(target.querySelector(".o_notebook li.o-web-studio-editor--element-clickable"));
        await click(target.querySelector(".o_web_studio_sidebar .o_web_studio_remove"));
        assert.strictEqual(
            target.querySelector(".modal-body").textContent,
            "Are you sure you want to remove this page from the view?",
            "should display the correct message"
        );
        await click(target.querySelector(".modal .btn-primary"));
        assert.strictEqual(editViewCount, 4, "should have edit the view 4 times");
    });

    QUnit.test(
        "disable creation(no_create options) in many2many_tags widget",
        async function (assert) {
            serverData.models.product.fields.m2m = {
                string: "M2M",
                type: "many2many",
                relation: "product",
            };

            const arch = /*xml*/ `
            <form>
                <sheet>
                    <group>
                        <field name='display_name'/>
                        <field name='m2m' widget='many2many_tags'/>
                    </group>
                </sheet>
            </form>`;

            const mockRPC = (route, args) => {
                if (route === "/web_studio/edit_view") {
                    assert.step("edit_view");
                    assert.equal(
                        args.operations[0].new_attrs.options,
                        '{"no_create":true}',
                        "no_create options should send with true value"
                    );
                }
            };

            await createViewEditor({
                serverData,
                mockRPC,
                type: "form",
                arch,
                resModel: "product",
            });

            await click(
                target.querySelector(".o_web_studio_view_renderer .o_field_many2many_tags")
            );
            assert.containsOnce(
                target,
                ".o_web_studio_sidebar #no_create",
                "should have no_create option for m2m field"
            );
            assert.containsNone(
                target,
                ".o_web_studio_sidebar #no_create:checked",
                "by default the no_create option should be false"
            );

            await click(target.querySelector(".o_web_studio_sidebar #no_create"));
            assert.verifySteps(["edit_view"]);
        }
    );

    QUnit.test(
        "disable creation(no_create options) in many2many_tags_avatar widget",
        async function (assert) {
            serverData.models.product.fields.m2m = {
                string: "M2M",
                type: "many2many",
                relation: "product",
            };

            const arch = `
            <form>
                <sheet>
                    <group>
                    <field name="m2m" widget="many2many_tags_avatar"/>
                    </group>
                </sheet>
            </form>`;
            await createViewEditor({
                serverData,
                type: "form",
                resModel: "product",
                arch,
                mockRPC: function (route, args) {
                    if (route === "/web_studio/edit_view") {
                        assert.step("edit_view");
                        assert.equal(
                            args.operations[0].new_attrs.options,
                            '{"no_create":true}',
                            "no_create options should send with true value"
                        );
                    }
                },
            });

            await click(
                target.querySelector(".o_web_studio_view_renderer .o_field_many2many_tags_avatar")
            );
            assert.containsOnce(
                target,
                ".o_web_studio_sidebar #no_create",
                "should have no_create option for many2many_tags_avatar widget"
            );
            assert.containsNone(
                target,
                ".o_web_studio_sidebar #no_create:checked",
                "by default the no_create option should be false"
            );

            await click(target.querySelector(".o_web_studio_sidebar #no_create"));
            assert.verifySteps(["edit_view"]);
        }
    );

    QUnit.test(
        "disable creation(no_create options) in many2many_avatar_user and many2many_avatar_employee widget",
        async function (assert) {
            const pyEnv = await startServer();

            const mailModels = pyEnv.getData();
            mailModels.product.fields.m2m_users = {
                string: "M2M Users",
                type: "many2many",
                relation: "res.users",
            };
            mailModels.product.fields.m2m_employees = {
                string: "M2M Employees",
                type: "many2many",
                relation: "hr.employee.public",
            };

            Object.assign(serverData.models, mailModels);
            setupManager.setupServiceRegistries();

            const arch = /*xml*/ `
            <form>
                <sheet>
                    <group>
                    <field name="m2m_users" widget="many2many_avatar_user"/>
                    </group>
                </sheet>
            </form>`;

            const mockRPC = (route, args) => {
                if (route === "/web_studio/edit_view") {
                    assert.step("edit_view");
                    assert.equal(
                        args.operations[0].new_attrs.options,
                        '{"no_create":true}',
                        "no_create options should send with true value"
                    );
                }
            };

            await createViewEditor({
                serverData,
                resModel: "product",
                type: "form",
                mockRPC,
                arch,
            });

            await click(
                target.querySelector(
                    '.o_web_studio_view_renderer .o_field_many2many_avatar_user[name="m2m_users"]'
                )
            );
            assert.containsOnce(
                target,
                ".o_web_studio_sidebar #no_create",
                "should have no_create option for many2many_avatar_user"
            );
            assert.containsNone(
                target,
                ".o_web_studio_sidebar #no_create:checked",
                "by default the no_create option should be false"
            );

            await click(target.querySelector(".o_web_studio_sidebar #no_create"));
            assert.verifySteps(["edit_view"]);
        }
    );

    QUnit.test("notebook and group drag and drop after a group", async function (assert) {
        assert.expect(2);
        const arch = `<form><sheet>
            <group>
            <field name='display_name'/>
            </group>
        </sheet></form>`;
        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch,
        });
        disableHookAnimation(target);
        const afterGroupHook = target.querySelector(".o_form_sheet > .o_web_studio_hook");

        const drag1 = await drag(
            target.querySelector(".o_web_studio_field_type_container .o_web_studio_field_tabs")
        );
        await drag1.moveTo(afterGroupHook);
        assert.containsOnce(
            target,
            ".o_web_studio_nearest_hook",
            "There should be 1 highlighted hook"
        );
        await drag1.cancel();

        const drag2 = await drag(
            target.querySelector(".o_web_studio_field_type_container .o_web_studio_field_columns")
        );
        await drag2.moveTo(afterGroupHook);
        assert.containsOnce(
            target,
            ".o_web_studio_nearest_hook",
            "There should be 1 highlighted hook"
        );
        await drag2.cancel();
    });

    QUnit.test("form: onchange is resilient to errors -- debug mode", async (assert) => {
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
            type: "form",
            resModel: "coucou",
            arch: `
            <form>
                <div class="rendered">
                    <field name="name" />
                </div>
            </form>`,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.step("onchange");
                    const error = new RPCError();
                    error.exceptionName = "odoo.exceptions.ValidationError";
                    error.code = 200;
                    return Promise.reject(error);
                }
            },
        });

        assert.verifySteps([
            "onchange",
            "The onchange triggered an error. It may indicate either a faulty call to onchange, or a faulty model python side",
        ]);
        assert.containsOnce(target, ".rendered");
    });

    QUnit.test("show an invisible x2many field", async (assert) => {
        serverData.models.partner.fields.o2m = {
            type: "one2many",
            relation: "product",
            string: "Products",
        };
        await createViewEditor({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `<form><group><field name='o2m' invisible="1" /></group></form>`,
        });

        assert.containsNone(target, "div[name='o2m']");
        await click(selectorContains(target, ".o_web_studio_sidebar .nav-link", "View"));
        await click(target.querySelector(".o_web_studio_sidebar #show_invisible"));
        assert.containsOnce(target, "div[name='o2m']");
    });

    QUnit.test("supports displaying <setting> tag in innergroup", async (assert) => {
        patchWithCleanup(Setting.prototype, {
            setup() {
                super.setup();
                assert.step(`setting instanciated. studioXpath: ${this.props.studioXpath}`);
            },
        });

        await createViewEditor({
            resModel: "partner",
            type: "form",
            serverData,
            arch: `<form>
            <group>
                <group class="o_settings_container">
                    <setting title="my setting">
                        <field name="display_name"/>
                    </setting>
                </group>
            </group>
            </form>`,
        });
        assert.containsOnce(target, ".o_setting_box .o_field_widget[name='display_name']");
        assert.verifySteps([
            "setting instanciated. studioXpath: /form[1]/group[1]/group[1]/setting[1]",
        ]);
    });

    QUnit.test("approval one rule by default", async function (assert) {
        assert.expect(8);
        const changeArch = makeArchChanger();

        let rules = [1];
        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch: `
                    <form>
                        <header>
                            <button name="0" string="Test" type="action" class="o_test_action_button"/>
                        </header>
                        <sheet>
                            <field name="m2o"/>
                        </sheet>
                    </form>
                `,
            resId: 1,
            mockRPC: function (route, args) {
                if (route === "/web_studio/get_studio_view_arch") {
                    return { studio_view_arch: "" };
                }
                if (route === "/web_studio/edit_view") {
                    changeArch(
                        args.view_id,
                        `
                        <form>
                            <header>
                                <button name="0" string="Test" type="action" class="o_test_action_button" studio_approval="True"/>
                            </header>
                            <sheet>
                                <field name="m2o"/>
                            </sheet>
                        </form>
                    `
                    );
                }
                if (route === "/web/dataset/call_kw/studio.approval.rule/create_rule") {
                    assert.strictEqual(
                        args.args[3],
                        "Test",
                        "button string is used to set the rule name"
                    );
                    return {};
                }
                if (route === "/web/dataset/call_kw/studio.approval.rule/write") {
                    return {};
                }
                if (route === "/web/dataset/call_kw/studio.approval.rule/get_approval_spec") {
                    return {
                        entries: [],
                        rules: rules.map((id) => ({
                            can_validate: true,
                            domain: false,
                            exclusive_user: false,
                            message: false,
                            responsible_id: false,
                            group_id: [1, "User types / Internal User"],
                            id,
                            users_to_notify: [],
                            notification_order: false,
                        })),
                    };
                }
            },
        });

        assert.containsOnce(
            target,
            ".o_form_statusbar button[name='0']",
            "there should be an action button"
        );

        await click(target, ".o_form_statusbar button[name='0']");
        await click(target, ".o_web_studio_sidebar_approval input[name='studio_approval']");
        assert.containsOnce(
            target,
            ".o_web_studio_sidebar_approval > .o_studio_sidebar_approval_rule",
            "there should be one rule"
        );
        assert.containsOnce(
            target,
            ".o_statusbar_buttons button img",
            "there should be one img in the button"
        );

        rules = [1, 2];
        await click(target, "a[name='create_approval_rule']");
        assert.containsN(
            target,
            ".o_web_studio_sidebar_approval > .o_studio_sidebar_approval_rule",
            2,
            "there should be two rule"
        );
        assert.containsN(
            target,
            ".o_statusbar_buttons button img",
            2,
            "there should be two img in the button"
        );

        rules = [1];
        await click(target.querySelectorAll(".o_approval_archive")[0]);
        assert.containsOnce(
            target,
            ".o_web_studio_sidebar_approval > .o_studio_sidebar_approval_rule",
            "there should be one rule"
        );
        assert.containsOnce(
            target,
            ".o_statusbar_buttons button img",
            "there should be one img in the button"
        );
    });

    QUnit.test("button rainbowman Truish value in sidebar", async function (assert) {
        const fakeHTTPService = {
            start() {
                return {};
            },
        };
        registry.category("services").add("http", fakeHTTPService);
        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch: `
                <form>
                <sheet>
                    <div class="oe_button_box" name="button_box">
                        <button name="action_confirm" type="object" effect="{}"/>
                    </div>
                </sheet>
                </form>`,
        });

        await click(target.querySelector("button.oe_stat_button[data-studio-xpath]"));
        assert.strictEqual(
            target.querySelector(".o_web_studio_sidebar [name='effect']").checked,
            true
        );
    });

    QUnit.test("button rainbowman False value in sidebar", async function (assert) {
        const fakeHTTPService = {
            start() {
                return {};
            },
        };
        registry.category("services").add("http", fakeHTTPService);
        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch: `
                <form>
                <sheet>
                    <div class="oe_button_box" name="button_box">
                        <button name="action_confirm" type="object" effect="False"/>
                    </div>
                </sheet>
                </form>`,
        });

        await click(target.querySelector("button.oe_stat_button[data-studio-xpath]"));
        assert.strictEqual(
            target.querySelector(".o_web_studio_sidebar [name='effect']").checked,
            false
        );
    });

    QUnit.test("edit the rainbowman effect from the sidebar", async function (assert) {
        assert.expect(8);

        let count = 0;
        const fakeHTTPService = {
            start() {
                return {};
            },
        };
        registry.category("services").add("http", fakeHTTPService);
        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch: `
                <form>
                <sheet>
                    <div class="oe_button_box" name="button_box">
                        <button name="action_confirm" type="object" effect="{'fadeout': 'medium'}"/>
                    </div>
                </sheet>
                </form>`,
            mockRPC: function (route, args) {
                if (route === "/web_studio/edit_view") {
                    assert.step("edit_view");
                    if (count === 0) {
                        assert.deepEqual(
                            args.operations[0].new_attrs,
                            {
                                effect: {
                                    fadeout: "fast",
                                },
                            },
                            "new fadeout value is being set properly"
                        );
                        const newArch = `
                            <form>
                                <sheet>
                                    <div class="oe_button_box" name="button_box">
                                        <button name="action_confirm" type="object" effect="{'fadeout': 'fast'}"/>
                                    </div>
                                </sheet>
                            </form>`;
                        return createMockViewResult(serverData, "form", newArch, "coucou");
                    } else {
                        assert.deepEqual(
                            args.operations[0].new_attrs,
                            {
                                effect: {},
                            },
                            "fadeout attribute has been removed from the effect"
                        );
                    }
                    count++;
                }
            },
        });

        await click(target.querySelector("button.oe_stat_button[data-studio-xpath]"));
        assert.strictEqual(
            target.querySelector(".o_web_studio_sidebar [name='effect']").checked,
            true
        );
        assert.strictEqual(
            target.querySelector(".o_web_studio_sidebar .o_select_menu .o_select_menu_toggler")
                .textContent,
            "Medium",
            "current value is displayed properly"
        );

        await editAnySelect(target, ".o_web_studio_sidebar .o_select_menu", "Fast");
        assert.verifySteps(["edit_view"]);

        await click(target.querySelector(".o_select_menu .o_select_menu_toggler_clear"));
        assert.verifySteps(["edit_view"]);
    });

    QUnit.test("supports multiple occurences of field", async (assert) => {
        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch: `<form><group>
                <field name="display_name" widget="phone" options="{'enable_sms': false}" />
                <field name="display_name" invisible="1" />
            </group></form>`,
        });

        assert.containsN(
            target,
            ".o_web_studio_form_view_editor .o_inner_group .o-web-studio-editor--element-clickable",
            1
        );
        await click(
            selectorContains(target, ".o_web_studio_sidebar .o_notebook_headers .nav-link", "View")
        );
        await click(target, ".o_web_studio_sidebar #show_invisible");
        assert.containsN(
            target,
            ".o_web_studio_form_view_editor .o_inner_group .o-web-studio-editor--element-clickable",
            2
        );

        await click(
            target.querySelectorAll(
                ".o_web_studio_form_view_editor .o_inner_group .o-web-studio-editor--element-clickable"
            )[0]
        );
        assert.strictEqual(
            target.querySelector(".o_web_studio_sidebar input[name='enable_sms']").checked,
            false
        ); // Would be true if not present in node's options

        await click(
            target.querySelectorAll(
                ".o_web_studio_form_view_editor .o_inner_group .o-web-studio-editor--element-clickable"
            )[1]
        );
        assert.strictEqual(
            target.querySelector(".o_web_studio_sidebar input[name='invisible']").checked,
            true
        );
    });

    QUnit.test(
        "Sets 'force_save' attribute when changing readonly attribute in form view",
        async function (assert) {
            assert.expect(4);

            const changeArch = makeArchChanger();
            const readonlyArch = `
                <form>
                    <field name='display_name' readonly="True"/>
                </form>`;
            const arch = `
                <form>
                    <field name='display_name'/>
                </form>`;
            let clickCount = 0;
            await createViewEditor({
                serverData,
                type: "form",
                resModel: "coucou",
                arch,
                mockRPC: (route, args) => {
                    if (route === "/web_studio/edit_view") {
                        const operation = args.operations[clickCount];
                        if (clickCount === 0) {
                            clickCount++;
                            assert.strictEqual(operation.new_attrs.readonly, "True");
                            assert.strictEqual(operation.new_attrs.force_save, "1");
                            changeArch(args.view_id, readonlyArch);
                        } else if (clickCount === 1) {
                            assert.strictEqual(operation.new_attrs.readonly, "False");
                            assert.strictEqual(operation.new_attrs.force_save, "0");
                            changeArch(args.view_id, arch);
                        }
                    }
                },
            });

            await click(target, ".o_web_studio_view_renderer .o_field_char");
            await click(target, '.o_web_studio_sidebar input[name="readonly"]');
            await click(target, '.o_web_studio_sidebar input[name="readonly"]');
        }
    );

    QUnit.test("X2Many field widgets not using subviews", async function (assert) {
        class NoSubView extends Component {
            static template = xml`<div>nosubview <t t-esc="this.props.record.fields[props.name].type"/></div>`;
        }
        registry.category("fields").add("nosubview", {
            component: NoSubView,
            supportedTypes: ["many2many", "one2many"],
        });

        serverData.models.coucou.fields.product_ids = { type: "one2many", relation: "product" };

        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            arch: '<form><field name="product_ids" widget="nosubview" /></form>',
        });

        assert.strictEqual(
            target.querySelector(".o_field_nosubview").textContent,
            "nosubview one2many"
        );
        assert.doesNotHaveClass(
            target.querySelector(".o_field_nosubview"),
            "o-web-studio-editor--element-clicked"
        );
        await click(target.querySelector(".o_field_nosubview"));
        assert.hasClass(
            target.querySelector(".o_field_nosubview"),
            "o-web-studio-editor--element-clicked"
        );
        assert.containsNone(target, ".o-web-studio-edit-x2manys-buttons");
    });

    QUnit.test("invisible relational are fetched", async (assert) => {
        serverData.models.coucou.fields.product_ids = { type: "one2many", relation: "product" };

        const mockRPC = (route, args) => {
            if (args.method === "web_read") {
                assert.step("web_read");
                assert.deepEqual(args.kwargs.specification, {
                    m2o: { fields: { display_name: {} } },
                    product_ids: { fields: {} },
                });
            }
        };

        await createViewEditor({
            serverData,
            type: "form",
            resModel: "coucou",
            resId: 1,
            arch: '<form><field name="product_ids" invisible="True" /><field name="m2o" invisible="True" /></form>',
            mockRPC,
        });

        assert.containsNone(target, ".o_field_widget");
        await click(selectorContains(target, ".o_web_studio_sidebar .nav-link", "View"));
        await click(target, ".o_web_studio_sidebar #show_invisible");
        assert.containsN(target, ".o_field_widget", 2);
        assert.verifySteps(["web_read"]);
    });

    QUnit.test("Auto save: don't auto-save a form editor", async function (assert) {
        await createViewEditor({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="display_name"/>
                    </group>
                </form>`,
            mockRPC(route, { args, method, model }) {
                if (method === "web_save" && model === "partner") {
                    assert.step("save"); // should be called
                    assert.deepEqual(args, [[1], { display_name: "test" }]);
                }
            },
        });

        assert.notStrictEqual(
            target.querySelector('.o_field_widget[name="display_name"]').value,
            "test"
        );

        const evnt = new Event("beforeunload");
        evnt.preventDefault = () => assert.step("prevented");
        window.dispatchEvent(evnt);
        await nextTick();
        assert.verifySteps([], "we should not save a form editor");
    });

    QUnit.test("fields in arch works correctly", async (assert) => {
        serverData.models.partner.fields = {
            partner_ids: { relation: "partner", type: "one2many" },
            some_field: { type: "char", string: "Some Field" },
        };
        serverData.models.partner.records = [];
        await createViewEditor({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="display_name"/>
                    <field name="partner_ids" >
                        <tree>
                            <field name="some_field" />
                        </tree>
                    </field>
                </form>`,
        });

        await click(target, ".o_web_studio_existing_fields_header");
        assert.strictEqual(
            target.querySelector(".o_web_studio_existing_fields").textContent,
            "Some FieldIDLast Modified onName"
        );
    });

    QUnit.test(
        "Restrict drag and drop of notebook and group in a inner group",
        async function (assert) {
            const arch = `<form>
            <sheet>
                <group>
                    <field name='display_name'/>
                </group>
            </sheet>
        </form>`;
            let editViewCount = 0;
            await createViewEditor({
                serverData,
                type: "form",
                resModel: "coucou",
                arch: arch,
                mockRPC: function (route, args) {
                    if (route === "/web_studio/edit_view") {
                        editViewCount++;
                        return createMockViewResult(serverData, "form", arch, "coucou");
                    }
                },
            });
            await dragAndDrop(
                target.querySelector(".o_web_studio_field_type_container .o_web_studio_field_tabs"),
                target.querySelector(".o_inner_group .o_wrap_field")
            );
            assert.strictEqual(editViewCount, 0, "the notebook cannot be dropped inside a group");
            await dragAndDrop(
                target.querySelector(
                    ".o_web_studio_field_type_container .o_web_studio_field_columns"
                ),
                target.querySelector(".o_inner_group .o_wrap_field")
            );
            assert.strictEqual(editViewCount, 0, "the group cannot be dropped inside a group");
        }
    );

    QUnit.test("edit_view route includes the context of the action", async (assert) => {
        registry.category("services").add("enterprise_subscription", {
            start() {
                return {};
            },
        });
        const action = {
            type: "ir.actions.act_window",
            xml_id: "coucou_action",
            res_model: "coucou",
            res_id: 1,
            views: [[1, "form"]],
            context: { action_key: "some_context_value" },
        };

        serverData.views = {
            "coucou,1,form": /*xml */ `
               <form>
                   <field name="display_name" />
               </form>`,
            "coucou,false,search": `<search />`,
        };

        const mockRPC = (route, args) => {
            if (route === "/web_studio/edit_view") {
                assert.step("edit_view");
                assert.strictEqual(args.context.action_key, "some_context_value");
            }
        };

        const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
        await doAction(webClient, action);
        await openStudio(target);
        await click(target, ".o_web_studio_form_view_editor div[name='display_name']");
        await editInput(target, ".o_web_studio_sidebar input[name='string']", "new Label");
        assert.verifySteps(["edit_view"]);
    });

    QUnit.test("subview's buttonbox form doesn't pollute main one", async (assert) => {
        serverData.models.coucou.fields.product_ids = { type: "one2many", relation: "product" };
        serverData.models.coucou.records = [{ id: 1, display_name: "Coucou 11", product_ids: [1] }];
        await createViewEditor({
            serverData,
            type: "form",
            arch: `<form>
                <field name="product_ids">
                    <form>
                        <div name="button_box">
                            <button name="some_action" type="object" string="my_action"/>
                        </div>
                        <field name="display_name" />
                    </form>
                    <tree><field name="display_name" /></tree>
                </field>
            </form>`,
            resModel: "coucou",
            resId: 1,
        });
        assert.containsOnce(target, ".o-form-buttonbox button");
        assert.hasClass(
            target.querySelector(".o-form-buttonbox button"),
            "o_web_studio_button_hook"
        );
        assert.containsNone(target, "button[name='some_action']");

        await click(target, ".o_field_x2many");
        await nextTick();
        await click(target, ".o_web_studio_editX2Many[data-type='form']");
        await nextTick();
        assert.containsOnce(target, ".o-form-buttonbox");
        assert.containsOnce(target, ".o-form-buttonbox button[name='some_action']");
    });

    QUnit.test("cannot add a related properties field", async (assert) => {
        serverData.models.coucou.fields.m2o = {
            type: "many2one",
            relation: "product",
            string: "m2o to product",
        };
        serverData.models.product.fields = {
            id: { type: "integer", string: "IDCusto" },
            properties: { type: "properties", string: "Product Properties" },
            some_test_field: { type: "char", string: "SomeTestField" },
        };
        serverData.models.product.records = [];
        await createViewEditor({
            serverData,
            type: "form",
            arch: '<form><group><field name="display_name" /></group></form>',
            resModel: "coucou",
        });
        disableHookAnimation(target);
        await dragAndDrop(
            ".o_web_studio_new_fields .o_web_studio_field_related",
            ".o_web_studio_form_view_editor .o_web_studio_hook"
        );
        assert.containsOnce(target, ".modal .o_model_field_selector");

        await click(target, ".modal .o_model_field_selector");
        await click(target, ".o_popover .o_model_field_selector_popover_item_relation");
        assert.deepEqual(
            [
                ...target.querySelectorAll(
                    ".o_popover .o_model_field_selector_popover_page .o_model_field_selector_popover_item"
                ),
            ].map((el) => el.textContent.trim()),
            ["Display Name", "IDCusto", "Last Modified on", "Name", "SomeTestField"]
        );
    });
});

QUnit.module("View Editors", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = getFormEditorServerData();

        serverData.models.coucou.fields.product_ids = { type: "one2many", relation: "product" };
        serverData.models.coucou.records = [{ id: 1, display_name: "Coucou 11", product_ids: [1] }];

        serverData.models.product.fields.m2m = {
            string: "M2M",
            type: "many2many",
            relation: "product",
        };
        serverData.models.product.records = [{ id: 1, display_name: "xpad" }];

        serverData.actions = {};
        serverData.views = {};

        serverData.actions["studio.coucou_action"] = {
            id: 99,
            xml_id: "studio.coucou_action",
            name: "coucouAction",
            res_model: "coucou",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
        };
        serverData.views["coucou,false,list"] = `<tree></tree>`;
        serverData.views["coucou,false,search"] = `<search></search>`;
        registerStudioDependencies();
    });

    QUnit.module("X2many Navigation");

    QUnit.test(
        "edit one2many form view (2 level) and check that the correct model is passed",
        async function (assert) {
            const action = serverData.actions["studio.coucou_action"];
            action.views = [[1, "form"]];
            action.res_model = "coucou";
            action.res_id = 1;
            serverData.views["coucou,1,form"] = /*xml */ `
               <form>
                   <sheet>
                       <field name="display_name"/>
                       <field name="product_ids">
                           <form>
                               <sheet>
                                <group>
                                   <field name="m2m" widget='many2many_tags'/>
                                </group>
                               </sheet>
                           </form>
                       </field>
                   </sheet>
               </form>`;

            Object.assign(serverData.views, {
                "product,2,list": "<tree><field name='display_name'/></tree>",
                "partner,3,list": "<tree><field name='display_name'/></tree>",
            });

            const webClient = await createEnterpriseWebClient({
                serverData,
                mockRPC: (route, args) => {
                    if (route === "/web_studio/edit_view") {
                        assert.step("edit_view");
                        assert.equal(args.model, "product");
                        assert.deepEqual(args.operations, [
                            {
                                type: "attributes",
                                target: {
                                    tag: "field",
                                    attrs: {
                                        name: "m2m",
                                    },
                                    xpath_info: [
                                        {
                                            tag: "form",
                                            indice: 1,
                                        },
                                        {
                                            tag: "sheet",
                                            indice: 1,
                                        },
                                        {
                                            tag: "group",
                                            indice: 1,
                                        },
                                        {
                                            tag: "field",
                                            indice: 1,
                                        },
                                    ],
                                    subview_xpath: "/form[1]/sheet[1]/field[2]/form[1]",
                                },
                                position: "attributes",
                                node: {
                                    tag: "field",
                                    attrs: {
                                        name: "m2m",
                                        widget: "many2many_tags",
                                        can_create: "true",
                                        can_write: "true",
                                    },
                                },
                                new_attrs: {
                                    options: '{"no_create":true}',
                                },
                            },
                        ]);
                    }
                },
            });
            await doAction(webClient, "studio.coucou_action");
            await openStudio(target);

            // edit the x2m form view
            await click(target.querySelector(".o_web_studio_form_view_editor .o_field_one2many"));
            await click(
                target.querySelector(
                    '.o_web_studio_form_view_editor .o_field_one2many .o_web_studio_editX2Many[data-type="form"]'
                )
            );
            await click(target.querySelector(".o_field_many2many_tags"));
            await click(target.querySelector(".o_web_studio_sidebar_checkbox #no_create"));
            assert.verifySteps(["edit_view"]);
        }
    );

    QUnit.test("display one2many without inline views", async function (assert) {
        serverData.models.product.fields.toughness = {
            manual: true,
            string: "toughness",
            type: "selection",
            selection: [
                ["0", "Hard"],
                ["1", "Harder"],
            ],
        };

        const action = serverData.actions["studio.coucou_action"];
        action.views = [[1, "form"]];
        action.res_model = "coucou";
        serverData.views["coucou,1,form"] = /*xml */ `
            <form>
                <sheet>
                    <field name='display_name'/>
                    <field name='product_ids' widget="one2many"/>
                </sheet>
            </form>`;
        serverData.views["coucou,false,search"] = `<search></search>`;
        serverData.views["product,2,list"] = `<tree><field name="toughness"/></tree>`;

        const mockRPC = (route, args) => {
            if (route === "/web_studio/create_inline_view") {
                assert.step("create_inline_view");
                const { model, field_name, subview_type, subview_xpath, view_id } = args;
                assert.strictEqual(model, "product");
                assert.strictEqual(field_name, "product_ids");
                assert.strictEqual(subview_type, "tree");
                assert.strictEqual(subview_xpath, "/form[1]/sheet[1]/field[2]");
                assert.strictEqual(view_id, 1);

                // hardcode inheritance mechanisme
                serverData.views["coucou,1,form"] = /*xml */ `
                    <form>
                        <sheet>
                            <field name='display_name'/>
                            <field name='product_ids'>${serverData.views["product,2,list"]}</field>
                        </sheet>
                    </form>`;
                return serverData.views["product,2,list"];
            }
        };

        const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
        await doAction(webClient, "studio.coucou_action");
        await openStudio(target);
        assert.containsOnce(target, ".o_field_one2many.o_field_widget");

        await click(target.querySelector(".o_web_studio_view_renderer .o_field_one2many"));
        await click(
            target.querySelector(
                '.o_web_studio_view_renderer .o_field_one2many .o_web_studio_editX2Many[data-type="list"]'
            )
        );
        assert.verifySteps(["create_inline_view"]);
    });

    QUnit.test("edit one2many list view", async function (assert) {
        // the 'More' button is only available in debug mode
        patchWithCleanup(odoo, { debug: true });

        const changeArch = makeArchChanger();

        serverData.models["ir.model.fields"] = {
            fields: {
                model: { type: "char" },
            },
            records: [{ id: 54, name: "coucou_id", model: "product" }],
        };
        serverData.views[
            "ir.model.fields,false,form"
        ] = `<form><field name="model" /><field name="id" /></form>`;
        serverData.views["ir.model.fields,false,search"] = `<search />`;

        serverData.models.product.fields.coucou_id = {
            type: "many2one",
            relation: "coucou",
            string: "coucouM2o",
        };

        const action = serverData.actions["studio.coucou_action"];
        action.views = [[1, "form"]];
        action.res_model = "coucou";
        serverData.views["coucou,1,form"] = /*xml */ `
            <form>
                <sheet>
                    <field name='display_name'/>
                    <field name='product_ids'>
                        <tree><field name='display_name'/></tree>
                    </field>
                </sheet>
            </form>`;
        serverData.views["coucou,false,search"] = `<search></search>`;

        const mockRPC = (route, args) => {
            assert.step(route);
            if (route === "/web_studio/get_default_value") {
                assert.step(`get_default_value: ${args.model_name}`);
                return Promise.resolve({});
            }
            if (args.method === "search_read" && args.model === "ir.model.fields") {
                assert.deepEqual(
                    args.kwargs.domain,
                    [
                        ["model", "=", "product"],
                        ["name", "=", "coucou_id"],
                    ],
                    "the model should be correctly set when editing field properties"
                );
            }
            if (route === "/web_studio/edit_view") {
                assert.strictEqual(args.view_id, 1);
                assert.strictEqual(args.operations.length, 1);

                const operation = args.operations[0];
                assert.strictEqual(operation.type, "add");
                assert.strictEqual(operation.position, "before");

                assert.deepEqual(operation.node, {
                    tag: "field",
                    attrs: {
                        name: "coucou_id",
                        optional: "show",
                    },
                });

                const target = operation.target;
                assert.deepEqual(target.attrs, { name: "display_name" });
                assert.strictEqual(target.tag, "field");
                assert.strictEqual(target.subview_xpath, "/form[1]/sheet[1]/field[2]/tree[1]");

                const newArch = /*xml */ `
                    <form>
                        <sheet>
                            <field name='display_name'/>
                            <field name='product_ids'>
                                <tree><field name='coucou_id'/><field name='display_name'/></tree>
                            </field>
                        </sheet>
                    </form>`;

                changeArch(args.view_id, newArch);
            }
        };

        const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
        await doAction(webClient, "studio.coucou_action");
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "/web/dataset/call_kw/coucou/get_views",
            "/web/dataset/call_kw/coucou/onchange",
        ]);
        await openStudio(target);
        assert.verifySteps([
            "/web/dataset/call_kw/coucou/get_views",
            "/web_studio/chatter_allowed",
            "/web_studio/get_studio_view_arch",
            "/web/dataset/call_kw/coucou/onchange",
        ]);

        await click(target.querySelector(".o_web_studio_view_renderer .o_field_one2many"));
        const blockOverlayZindex = target.querySelector(
            ".o_web_studio_view_renderer .o_field_one2many .o-web-studio-edit-x2manys-buttons"
        ).style["z-index"];
        assert.strictEqual(blockOverlayZindex, "1000", "z-index of blockOverlay should be 1000");
        assert.verifySteps(["/web_studio/get_default_value", "get_default_value: coucou"]);

        await click(
            target.querySelector(
                ".o_web_studio_view_renderer .o_field_one2many .o_web_studio_editX2Many"
            )
        );
        assert.verifySteps(["/web/dataset/call_kw/product/fields_get"]);
        assert.containsOnce(
            target,
            ".o_web_studio_view_renderer thead tr [data-studio-xpath]",
            "there should be 1 nodes in the x2m editor."
        );

        await click(target.querySelector(".o_web_studio_existing_fields_header"));
        await dragAndDrop(
            ".o_web_studio_existing_fields_section .o_web_studio_field_many2one",
            ".o_web_studio_hook"
        );
        await nextTick();
        assert.verifySteps(["/web_studio/edit_view"]);

        assert.containsN(
            target,
            ".o_web_studio_view_renderer thead tr [data-studio-xpath]",
            2,
            "there should be 2 nodes after the drag and drop."
        );

        // click on a field in the x2m list view
        await click(target.querySelector(".o_web_studio_view_renderer [data-studio-xpath]"));

        // edit field properties
        assert.containsOnce(
            target,
            ".o_web_studio_sidebar .o_web_studio_parameters",
            "there should be button to edit the field properties"
        );
        await click(target.querySelector(".o_web_studio_sidebar .o_web_studio_parameters"));
        assert.verifySteps([
            "/web/dataset/call_kw/ir.model.fields/search_read",
            "/web/dataset/call_kw/ir.model.fields/get_views",
            "/web/dataset/call_kw/ir.model.fields/web_read",
        ]);
    });

    QUnit.test(
        "edit one2many list view with widget fieldDependencies and some records",
        async function (assert) {
            serverData.models.product.fields.is_dep = {
                type: "char",
                string: "Dependency from fields_get",
            };
            serverData.models.coucou.records[0] = {
                id: 1,
                display_name: "coucou1",
                product_ids: [1],
            };
            serverData.models.product.records[0] = {
                id: 1,
                is_dep: "the meters",
                display_name: "people say",
            };

            const charField = registry.category("fields").get("char");
            class CharWithDependencies extends charField.component {
                setup() {
                    super.setup();
                    const record = this.props.record;
                    onMounted(() => {
                        assert.step(
                            `widget Dependency: ${JSON.stringify(record.fields.is_dep)} : ${
                                record.data.is_dep
                            }`
                        );
                    });
                }
            }
            registry.category("fields").add("list.withDependencies", {
                ...charField,
                component: CharWithDependencies,
                fieldDependencies: [{ name: "is_dep", type: "char" }],
            });

            const action = serverData.actions["studio.coucou_action"];
            action.res_id = 1;
            action.views = [[1, "form"]];
            action.res_model = "coucou";
            serverData.views["coucou,1,form"] = /*xml */ `<form>
            <sheet>
                <field name='display_name'/>
                <field name='product_ids'>
                    <tree><field name='display_name' widget="withDependencies"/></tree>
                </field>
            </sheet>
        </form>`;
            const mockRPC = (route, args) => {
                if (args.method === "fields_get") {
                    assert.step("fields_get");
                }
            };
            const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
            await doAction(webClient, "studio.coucou_action");
            assert.verifySteps([
                `widget Dependency: {"name":"is_dep","type":"char","readonly":true} : the meters`,
            ]);
            await openStudio(target);
            assert.verifySteps([
                `widget Dependency: {"name":"is_dep","type":"char","readonly":true} : the meters`,
            ]);

            assert.containsOnce(target, ".o_web_studio_form_view_editor");
            await click(target.querySelector(".o_field_one2many"));
            await click(target.querySelector(".o_field_one2many .o_web_studio_editX2Many"));

            assert.verifySteps([
                "fields_get",
                `widget Dependency: {"type":"char","string":"Dependency from fields_get","name":"is_dep"} : the meters`,
            ]);
            assert.containsOnce(target, ".o_web_studio_list_view_editor");
        }
    );

    QUnit.test("entering x2many with view widget", async (assert) => {
        class MyWidget extends Component {}
        MyWidget.template = xml`<div class="myWidget" />`;
        const myWidget = {
            component: MyWidget,
        };
        registry.category("view_widgets").add("myWidget", myWidget);

        serverData.models.coucou.records[0] = {
            id: 1,
            display_name: "coucou1",
            product_ids: [1],
        };
        serverData.models.product.records[0] = {
            id: 1,
            display_name: "people say",
        };

        const action = serverData.actions["studio.coucou_action"];
        action.res_id = 1;
        action.views = [[1, "form"]];
        action.res_model = "coucou";
        serverData.views["coucou,1,form"] = /*xml */ `<form>
            <sheet>
                <field name='display_name'/>
                <field name='product_ids'>
                    <tree><widget name="myWidget"/></tree>
                </field>
            </sheet>
        </form>`;
        const webClient = await createEnterpriseWebClient({ serverData });
        await doAction(webClient, "studio.coucou_action");
        await openStudio(target);

        assert.containsOnce(target, ".o_web_studio_form_view_editor");
        assert.containsOnce(target, ".myWidget");

        await click(target, ".o_web_studio_view_renderer .o_field_one2many");
        await click(
            target,
            ".o_web_studio_view_renderer .o_field_one2many .o_web_studio_editX2Many[data-type='list']"
        );
        assert.containsOnce(target, ".o_web_studio_list_view_editor");
        assert.containsOnce(target, ".myWidget");
    });

    QUnit.test("edit one2many list view with tree_view_ref context key", async function (assert) {
        const action = serverData.actions["studio.coucou_action"];
        action.views = [[1, "form"]];
        action.res_model = "coucou";
        serverData.views["coucou,1,form"] = /*xml */ `
            <form>
                <sheet>
                    <field name='display_name'/>
                    <field name='product_ids' widget="one2many" context="{'tree_view_ref': 'module.tree_view_ref'}" />
                </sheet>
            </form>`;

        serverData.views["coucou,false,search"] = `<search></search>`;
        serverData.views[
            "product,module.tree_view_ref,list"
        ] = /*xml */ `<tree><field name="display_name"/></tree>`;

        const mockRPC = (route, args) => {
            if (route === "/web_studio/create_inline_view") {
                assert.step("create_inline_view");
                assert.equal(
                    args.context.tree_view_ref,
                    "module.tree_view_ref",
                    "context tree_view_ref should be propagated for inline view creation"
                );

                const { model, field_name, subview_type, subview_xpath, view_id } = args;
                assert.strictEqual(model, "product");
                assert.strictEqual(field_name, "product_ids");
                assert.strictEqual(subview_type, "tree");
                assert.strictEqual(subview_xpath, "/form[1]/sheet[1]/field[2]");
                assert.strictEqual(view_id, 1);

                // hardcode inheritance mechanisme
                serverData.views["coucou,1,form"] = /*xml */ `
                    <form>
                        <sheet>
                            <field name='display_name'/>
                            <field name='product_ids'>${serverData.views["product,module.tree_view_ref,list"]}</field>
                        </sheet>
                    </form>`;
                return serverData.views["product,module.tree_view_ref,list"];
            }
        };

        const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
        await doAction(webClient, "studio.coucou_action");
        await openStudio(target);

        await click(target.querySelector(".o_web_studio_view_renderer .o_field_one2many"));
        await click(
            target.querySelector(
                ".o_web_studio_view_renderer .o_field_one2many .o_web_studio_editX2Many"
            )
        );
        assert.verifySteps(["create_inline_view"]);
    });

    QUnit.test(
        "edit one2many form view (2 level) and check chatter allowed",
        async function (assert) {
            const pyEnv = await startServer();

            const partnerId = pyEnv["partner"].create({
                name: "jean",
            });

            const productId = pyEnv["product"].create({
                display_name: "xpad",
                partner_ids: [[5], [4, partnerId, false]],
            });

            const coucouId1 = pyEnv["coucou"].create({
                display_name: "Coucou 11",
                product_ids: [[5], [4, productId, false]],
            });

            const action = serverData.actions["studio.coucou_action"];
            action.views = [[1, "form"]];
            action.res_model = "coucou";
            action.res_id = coucouId1;
            serverData.views["coucou,1,form"] = /*xml */ `
            <form>
                <sheet>
                    <field name='display_name'/>
                    <field name='product_ids'>
                        <form>
                            <sheet>
                                <group>
                                    <field name='partner_ids'>
                                        <form><sheet><group><field name='display_name'/></group></sheet></form>
                                    </field>
                                </group>
                            </sheet>
                        </form>
                    </field>
                </sheet>
            </form>`;

            Object.assign(serverData.views, {
                "product,2,list": "<tree><field name='display_name'/></tree>",
                "partner,3,list": "<tree><field name='display_name'/></tree>",
            });

            serverData.views["coucou,false,search"] = `<search></search>`;

            const mockRPC = (route, args) => {
                if (route !== "/hr_attendance/attendance_user_data") {
                    assert.step(route);
                }
                if (route === "/web_studio/chatter_allowed") {
                    return true;
                }
                if (args.method === "name_search" && args.model === "ir.model.fields") {
                    assert.deepEqual(
                        args.kwargs.args,
                        [
                            ["relation", "=", "partner"],
                            ["ttype", "in", ["many2one", "many2many"]],
                            ["store", "=", true],
                        ],
                        "the domain should be correctly set when searching for a related field for new button"
                    );
                    return [[1, "Partner"]];
                }
            };

            const { webClient } = await start({
                serverData,
                mockRPC,
            });

            assert.verifySteps([
                "/web/webclient/load_menus",
                "/mail/init_messaging",
                "/mail/load_message_failures",
                "/web/dataset/call_kw/res.users/systray_get_activities",
            ]);

            await doAction(webClient, "studio.coucou_action");
            assert.verifySteps([
                "/web/action/load",
                "/web/dataset/call_kw/coucou/get_views",
                "/web/dataset/call_kw/coucou/web_read",
            ]);
            await openStudio(target);
            assert.verifySteps([
                "/web/dataset/call_kw/coucou/get_views",
                "/web_studio/chatter_allowed",
                "/web_studio/get_studio_view_arch",
                "/web/dataset/call_kw/coucou/web_read",
            ]);

            assert.containsOnce(
                target,
                ".o_web_studio_add_chatter",
                "should be possible to add a chatter"
            );

            await click(target.querySelector(".o_web_studio_view_renderer .o_field_one2many"));
            assert.verifySteps(["/web_studio/get_default_value"]);

            await click(
                target.querySelector(
                    '.o_web_studio_view_renderer .o_field_one2many .o_web_studio_editX2Many[data-type="form"]'
                )
            );
            assert.containsNone(
                target,
                ".o_web_studio_add_chatter",
                "should not be possible to add a chatter"
            );
            assert.verifySteps([
                "/web/dataset/call_kw/product/fields_get",
                "/web/dataset/call_kw/partner/get_views",
                "/web/dataset/call_kw/product/web_read",
            ]);

            await click(target.querySelector(".o_web_studio_view_renderer .o_field_one2many"));
            assert.verifySteps(["/web_studio/get_default_value"]);
            await click(
                target.querySelector(
                    '.o_web_studio_view_renderer .o_field_one2many .o_web_studio_editX2Many[data-type="form"]'
                )
            );
            assert.verifySteps([
                "/web/dataset/call_kw/partner/fields_get",
                "/web/dataset/call_kw/partner/web_read",
            ]);

            assert.strictEqual(
                target.querySelector(".o_field_char").textContent,
                "jean",
                "the partner view form should be displayed."
            );

            disableHookAnimation(target);
            await dragAndDrop(
                target.querySelector(".o_web_studio_new_fields .o_web_studio_field_char"),
                target.querySelector(".o_inner_group .o_web_studio_hook")
            );
            assert.verifySteps(["/web_studio/edit_view", "/web/dataset/call_kw/partner/web_read"]);

            // add a new button
            await click(
                target.querySelector(".o_web_studio_form_view_editor .o_web_studio_button_hook")
            );
            assert.verifySteps([]);

            assert.containsOnce(target, ".modal .o_web_studio_new_button_dialog");
            await click(
                target.querySelector(
                    ".modal .o_web_studio_new_button_dialog .o_input_dropdown input"
                )
            );
            assert.verifySteps(["/web/dataset/call_kw/ir.model.fields/name_search"]);
            await click(target.querySelector(".modal .o_web_studio_new_button_dialog li a"));
            assert.strictEqual(
                target.querySelector(
                    ".modal .o_web_studio_new_button_dialog .o-autocomplete--input"
                ).value,
                "Partner"
            );
        }
    );

    QUnit.test(
        "edit one2many list view that uses parent key [REQUIRE FOCUS]",
        async function (assert) {
            const pyEnv = await startServer();

            const partnerId = pyEnv["partner"].create({
                name: "jacques",
            });

            const productId = pyEnv["product"].create({
                display_name: "xpad",
                m2o: partnerId,
            });

            const coucouId1 = pyEnv["coucou"].create({
                display_name: "Coucou 11",
                product_ids: [[5], [4, productId, false]],
            });

            const action = serverData.actions["studio.coucou_action"];
            action.views = [[1, "form"]];
            action.res_model = "coucou";
            action.res_id = coucouId1;
            serverData.views["coucou,1,form"] = /*xml */ `
           <form>
                <sheet>
                    <field name='display_name'/>
                    <field name='product_ids'>
                        <form>
                            <sheet>
                                <field name="m2o"
                                       invisible="parent.display_name == 'coucou'"
                                       domain="[('display_name', '=', parent.display_name)]" />
                            </sheet>
                        </form>
                    </field>
                </sheet>
            </form>`;

            Object.assign(serverData.views, {
                "product,2,list": "<tree><field name='display_name'/></tree>",
            });

            serverData.views["coucou,false,search"] = `<search></search>`;

            registry.category("services").add("field", fieldService);

            const mockRPC = function (route, args) {
                if (route === "/web_studio/edit_view") {
                    // Make sure attrs are overridden by empty object to remove the domain
                    assert.deepEqual(args.operations[0].new_attrs, { invisible: "False" });
                    assert.step("edit view");
                }
            };

            const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
            await doAction(webClient, "studio.coucou_action");
            await openStudio(target);

            // edit the x2m form view
            await click(target.querySelector(".o_web_studio_form_view_editor .o_field_one2many"));
            await click(
                target.querySelector(
                    '.o_web_studio_form_view_editor .o_field_one2many .o_web_studio_editX2Many[data-type="form"]'
                )
            );
            assert.strictEqual(
                target.querySelector('.o_web_studio_form_view_editor .o_field_widget[name="m2o"]')
                    .textContent,
                "jacques",
                "the x2m form view should be correctly rendered"
            );
            await click(
                target.querySelector('.o_web_studio_form_view_editor .o_field_widget[name="m2o"]')
            );

            // open the domain editor
            assert.containsNone(target, ".modal");
            assert.strictEqual(
                target.querySelector(".o_web_studio_sidebar input#domain").value,
                "[('display_name', '=', parent.display_name)]"
            );

            await click(target.querySelector(".o_web_studio_sidebar input#domain"));
            assert.containsOnce(target, ".modal");
            assert.strictEqual(
                target.querySelector(".modal .modal-body").textContent,
                "Matchallof the following rules:Display Name=!=containsdoes not containis inis not inis setis not setparent.display_nameNew Rule"
            );

            // Close the modal and remove the domain on invisible attr
            await click(target.querySelector(".btn-close"));
            await click(target.querySelector("#invisible"));
            assert.verifySteps(["edit view"]);
        }
    );

    QUnit.test("move a field in one2many list", async function (assert) {
        const pyEnv = await startServer();

        const coucouId1 = pyEnv["coucou"].create({
            display_name: "Coucou 11",
            product_ids: pyEnv["product"].search([["display_name", "=", "xpad"]]),
        });

        const action = serverData.actions["studio.coucou_action"];
        action.views = [[1, "form"]];
        action.res_model = "coucou";
        action.res_id = coucouId1;
        serverData.views["coucou,1,form"] = /*xml */ `
            <form>
                <sheet>
                    <field name='display_name'/>
                    <field name='product_ids'>
                        <tree>
                            <field name='m2o'/>
                            <field name='coucou_id'/>
                        </tree>
                    </field>
                </sheet>
            </form>`;

        serverData.views["coucou,false,search"] = `<search></search>`;

        const mockRPC = (route, args) => {
            if (route === "/web_studio/edit_view") {
                assert.step("edit_view");
                assert.deepEqual(
                    args.operations[0],
                    {
                        node: {
                            tag: "field",
                            attrs: { name: "coucou_id" },
                            subview_xpath: "/form[1]/sheet[1]/field[2]/tree[1]",
                            xpath_info: [
                                {
                                    indice: 1,
                                    tag: "tree",
                                },
                                {
                                    indice: 2,
                                    tag: "field",
                                },
                            ],
                        },
                        position: "before",
                        target: {
                            tag: "field",
                            attrs: { name: "m2o" },
                            subview_xpath: "/form[1]/sheet[1]/field[2]/tree[1]",
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
            }
        };

        const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
        await doAction(webClient, "studio.coucou_action");
        await openStudio(target);

        // edit the x2m form view
        await click(target.querySelector(".o_web_studio_form_view_editor .o_field_one2many"));
        await click(
            target.querySelector(
                '.o_web_studio_form_view_editor .o_field_one2many .o_web_studio_editX2Many[data-type="list"]'
            )
        );

        assert.strictEqual(
            Array.from(target.querySelectorAll(".o_web_studio_list_view_editor th"))
                .map((el) => el.textContent)
                .join(""),
            "M2Ocoucou",
            "the columns should be in the correct order"
        );

        // move coucou at index 0
        await dragAndDrop(
            selectorContains(target, ".o_web_studio_list_view_editor th", "coucou"),
            target.querySelector("th.o_web_studio_hook")
        );
        assert.verifySteps(["edit_view"]);
    });

    QUnit.test("One2Many list editor column_invisible in attrs ", async function (assert) {
        const pyEnv = await startServer();
        pyEnv["coucou"].create({
            display_name: "Coucou 11",
            product_ids: pyEnv["product"].search([["display_name", "=", "xpad"]]),
        });

        const action = serverData.actions["studio.coucou_action"];
        action.views = [[1, "form"]];
        action.res_model = "coucou";
        serverData.views["coucou,1,form"] = /*xml */ `
        <form>
            <field name='product_ids'>
                <tree>
                    <field name="display_name" column_invisible="not parent.id" />
                </tree>
            </field>
        </form>`;

        serverData.views["coucou,false,search"] = `<search></search>`;

        const mockRPC = (route, args) => {
            if (route === "/web_studio/edit_view") {
                assert.step("edit_view");
                assert.deepEqual(
                    args.operations[0].new_attrs,
                    { readonly: "True" },
                    'we should send "column_invisible" in attrs'
                );
            }
        };

        const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
        await doAction(webClient, "studio.coucou_action");
        await openStudio(target);

        // Enter edit mode of the O2M
        await click(target.querySelector(".o_field_one2many[name=product_ids]"));
        await click(target.querySelector('.o_web_studio_editX2Many[data-type="list"]'));

        await click(selectorContains(target, ".o_web_studio_sidebar .nav-link", "View"));
        await click(target.querySelector(".o_web_studio_sidebar input#show_invisible"));

        // select the first column
        await click(target.querySelector("thead th[data-studio-xpath]"));
        // enable readonly
        await click(target.querySelector(".o_web_studio_sidebar input#readonly"));
        assert.verifySteps(["edit_view"]);
    });

    QUnit.test(
        "One2Many form datapoint doesn't contain the parent datapoint",
        async function (assert) {
            /*
             * OPW-2125214
             * When editing a child o2m form with studio, the fields_get method tries to load
             * the parent fields too. This is not allowed anymore by the ORM.
             * It happened because, before, the child datapoint contained the parent datapoint's data
             */
            assert.expect(1);
            const pyEnv = await startServer();
            const coucouId1 = pyEnv["coucou"].create({
                display_name: "Coucou 11",
                product_ids: [],
            });

            const action = serverData.actions["studio.coucou_action"];
            action.views = [[1, "form"]];
            action.res_model = "coucou";
            action.res_id = coucouId1;
            serverData.views["coucou,1,form"] = /*xml */ `
           <form>
               <field name='product_ids'>
                    <form>
                        <field name="display_name" />
                        <field name="toughness" />
                    </form>
               </field>
           </form>`;

            serverData.views["coucou,false,search"] = `<search></search>`;
            serverData.views["product,2,list"] = `<tree><field name="display_name" /></tree>`;

            const mockRPC = async (route, args) => {
                if (args.method === "onchange" && args.model === "product") {
                    const fields = args.args[3];
                    assert.deepEqual(Object.keys(fields), ["display_name", "toughness"]);
                }
            };

            const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
            await doAction(webClient, "studio.coucou_action");
            await openStudio(target);

            await click(target.querySelector(".o_web_studio_form_view_editor .o_field_one2many"));
            await click(
                target.querySelector(
                    '.o_web_studio_form_view_editor .o_field_one2many .o_web_studio_editX2Many[data-type="form"]'
                )
            );
        }
    );

    QUnit.test("navigate in nested x2many which has a context", async function (assert) {
        serverData.models.product.fields.po2m = {
            type: "one2many",
            relation: "partner",
            string: "Po2M",
        };
        const action = serverData.actions["studio.coucou_action"];
        action.views = [[1, "form"]];
        action.res_model = "coucou";
        action.res_id = 1;
        serverData.views["coucou,1,form"] = /*xml */ `
           <form>
                <field name='product_ids'>
                    <form>
                        <div class="product-subview-form" />
                        <field name="po2m" context="{'context_key': 'value', 'parent': parent.id}">
                            <form>
                                <div class="po2m-subview-form" />
                                <field name="display_name" />
                            </form>
                        </field>
                    </form>
               </field>
           </form>`;

        serverData.views["coucou,false,search"] = `<search></search>`;
        serverData.views["product,2,list"] = `<tree><field name="display_name" /></tree>`;
        serverData.views["partner,false,list"] = `<tree><field name="display_name" /></tree>`;

        const webClient = await createEnterpriseWebClient({ serverData });
        await doAction(webClient, "studio.coucou_action");
        await openStudio(target);

        await click(target.querySelector(".o_web_studio_form_view_editor .o_field_one2many"));
        await click(
            target.querySelector(
                '.o_web_studio_form_view_editor .o_field_one2many .o_web_studio_editX2Many[data-type="form"]'
            )
        );

        assert.containsOnce(target, ".o_view_controller .product-subview-form");

        await click(target.querySelector(".o_web_studio_form_view_editor .o_field_one2many"));
        await click(
            target.querySelector(
                '.o_web_studio_form_view_editor .o_field_one2many .o_web_studio_editX2Many[data-type="form"]'
            )
        );

        assert.containsOnce(target, ".o_view_controller .po2m-subview-form");
    });

    QUnit.test("navigate in x2many form which some field has a context", async function (assert) {
        serverData.models.product.fields.m2o = {
            type: "many2one",
            relation: "partner",
            string: "m2o",
        };
        const action = serverData.actions["studio.coucou_action"];
        action.views = [[1, "form"]];
        action.res_model = "coucou";
        action.res_id = 1;
        serverData.views["coucou,1,form"] = /*xml */ `
           <form>
                <field name='product_ids'>
                    <form>
                        <div class="product-subview-form" />
                        <field name="m2o" context="{'context_key': 'value', 'parent': parent.id}" />
                    </form>
               </field>
           </form>`;

        serverData.views["coucou,false,search"] = `<search></search>`;
        serverData.views["product,2,list"] = `<tree><field name="display_name" /></tree>`;
        serverData.views["partner,false,list"] = `<tree><field name="display_name" /></tree>`;

        const webClient = await createEnterpriseWebClient({ serverData });
        await doAction(webClient, "studio.coucou_action");
        await openStudio(target);

        await click(target.querySelector(".o_web_studio_form_view_editor .o_field_one2many"));
        await click(
            target.querySelector(
                '.o_web_studio_form_view_editor .o_field_one2many .o_web_studio_editX2Many[data-type="form"]'
            )
        );

        assert.containsOnce(target, ".o_view_controller .product-subview-form");
    });

    QUnit.test(
        "navigate in x2many form which some field has a context -- context in action",
        async function (assert) {
            serverData.models.product.fields.m2o = {
                type: "many2one",
                relation: "partner",
                string: "m2o",
            };
            const action = serverData.actions["studio.coucou_action"];
            action.context = { action_context_key: "couac" };
            action.views = [[1, "form"]];
            action.res_model = "coucou";
            action.res_id = 1;
            serverData.views["coucou,1,form"] = /*xml */ `
           <form>
                <field name='product_ids'>
                    <form>
                        <div class="product-subview-form" />
                        <field name="m2o" context="{'context_key': 'value', 'parent': parent.id}" />
                    </form>
               </field>
           </form>`;

            serverData.views["coucou,false,search"] = `<search></search>`;
            serverData.views["product,2,list"] = `<tree><field name="display_name" /></tree>`;
            serverData.views["partner,false,list"] = `<tree><field name="display_name" /></tree>`;

            const webClient = await createEnterpriseWebClient({ serverData });
            await doAction(webClient, "studio.coucou_action");
            await openStudio(target);

            await click(target.querySelector(".o_web_studio_form_view_editor .o_field_one2many"));
            await click(
                target.querySelector(
                    '.o_web_studio_form_view_editor .o_field_one2many .o_web_studio_editX2Many[data-type="form"]'
                )
            );

            assert.containsOnce(target, ".o_view_controller .product-subview-form");
        }
    );

    QUnit.test(
        "navigate in x2many form which some field has a context -- context in action with records in relation",
        async function (assert) {
            serverData.models.product.fields.m2o = {
                type: "many2one",
                relation: "partner",
                string: "m2o",
            };

            serverData.models.partner.records = [{ id: 1, display_name: "couic" }];
            serverData.models.product.records = [{ id: 1, display_name: "xpad", m2o: [1] }];
            const action = serverData.actions["studio.coucou_action"];
            action.context = { action_context_key: "couac" };
            action.views = [[1, "form"]];
            action.res_model = "coucou";
            action.res_id = 1;
            serverData.views["coucou,1,form"] = /*xml */ `
           <form>
                <field name='product_ids'>
                    <form>
                        <div class="product-subview-form" />
                        <field name="m2o" context="{'context_key': 'value', 'parent': parent.id}" />
                    </form>
               </field>
           </form>`;

            serverData.views["coucou,false,search"] = `<search></search>`;
            serverData.views["product,2,list"] = `<tree><field name="display_name" /></tree>`;
            serverData.views["partner,false,list"] = `<tree><field name="display_name" /></tree>`;

            const webClient = await createEnterpriseWebClient({ serverData });
            await doAction(webClient, "studio.coucou_action");
            await openStudio(target);

            await click(target.querySelector(".o_web_studio_form_view_editor .o_field_one2many"));
            await click(
                target.querySelector(
                    '.o_web_studio_form_view_editor .o_field_one2many .o_web_studio_editX2Many[data-type="form"]'
                )
            );

            assert.containsOnce(target, ".o_view_controller .product-subview-form");
            assert.strictEqual(target.querySelector(".o_field_many2one").textContent, "couic");
        }
    );

    QUnit.test(
        "navigate in x2many form which some field has a context -- with records in relation",
        async function (assert) {
            serverData.models.product.fields.m2o = {
                type: "many2one",
                relation: "partner",
                string: "m2o",
            };
            serverData.models.partner.records = [{ id: 1, display_name: "couic" }];
            serverData.models.product.records = [{ id: 1, display_name: "xpad", m2o: [1] }];

            const action = serverData.actions["studio.coucou_action"];
            action.views = [[1, "form"]];
            action.res_model = "coucou";
            action.res_id = 1;
            serverData.views["coucou,1,form"] = /*xml */ `
           <form>
                <field name='product_ids'>
                    <form>
                        <div class="product-subview-form" />
                        <field name="m2o" context="{'context_key': 'value', 'parent': parent.id}" />
                    </form>
               </field>
           </form>`;

            serverData.views["coucou,false,search"] = `<search></search>`;
            serverData.views["product,2,list"] = `<tree><field name="display_name" /></tree>`;
            serverData.views["partner,false,list"] = `<tree><field name="display_name" /></tree>`;

            const webClient = await createEnterpriseWebClient({ serverData });
            await doAction(webClient, "studio.coucou_action");
            await openStudio(target);

            await click(target.querySelector(".o_web_studio_form_view_editor .o_field_one2many"));
            await click(
                target.querySelector(
                    '.o_web_studio_form_view_editor .o_field_one2many .o_web_studio_editX2Many[data-type="form"]'
                )
            );

            assert.containsOnce(target, ".o_view_controller .product-subview-form");
            assert.strictEqual(target.querySelector(".o_field_many2one").textContent, "couic");
        }
    );

    QUnit.test(
        "navigate in x2many list which some field has a context -- with records in relation",
        async function (assert) {
            serverData.models.product.fields.m2o = {
                type: "many2one",
                relation: "partner",
                string: "m2o",
            };

            serverData.models.partner.records = [{ id: 1, display_name: "couic" }];
            serverData.models.product.records = [{ id: 1, display_name: "xpad", m2o: [1] }];

            const action = serverData.actions["studio.coucou_action"];
            action.views = [[1, "form"]];
            action.res_model = "coucou";
            action.res_id = 1;
            serverData.views["coucou,1,form"] = /*xml */ `
           <form>
                <field name='product_ids'>
                    <tree>
                        <field name="display_name" />
                        <field name="m2o" context="{'context_key': 'value', 'parent': parent.id}" />
                    </tree>
               </field>
           </form>`;

            serverData.views["coucou,false,search"] = `<search></search>`;
            serverData.views["product,2,list"] = `<tree><field name="display_name" /></tree>`;
            serverData.views["partner,false,list"] = `<tree><field name="display_name" /></tree>`;

            const webClient = await createEnterpriseWebClient({ serverData });
            await doAction(webClient, "studio.coucou_action");
            await openStudio(target);

            await click(target.querySelector(".o_web_studio_form_view_editor .o_field_one2many"));
            await click(
                target.querySelector(
                    '.o_web_studio_form_view_editor .o_field_one2many .o_web_studio_editX2Many[data-type="list"]'
                )
            );

            assert.strictEqual(
                target.querySelector(".o_view_controller.o_list_view .o_data_row .o_list_many2one")
                    .textContent,
                "couic"
            );
        }
    );
});
