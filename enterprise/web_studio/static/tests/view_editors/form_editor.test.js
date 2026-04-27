import { expect, test } from "@odoo/hoot";
import { animationFrame, queryAll, waitFor } from "@odoo/hoot-dom";
import { Component, onMounted, xml } from "@odoo/owl";

import {
    contains,
    defineModels,
    fields,
    models,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { charField } from "@web/views/fields/char/char_field";
import { ImageField } from "@web/views/fields/image/image_field";
import { COMPUTED_DISPLAY_OPTIONS } from "@web_studio/client_action/view_editor/interactive_editor/properties/type_widget_properties/type_specific_and_computed_properties";

import { editView, mountViewEditor } from "@web_studio/../tests/view_editor_tests_utils";
import { formEditor } from "@web_studio/client_action/view_editor/editors/form/form_editor";

class Coucou extends models.Model {
    display_name = fields.Char();
    m2o = fields.Many2one({ string: "Product", relation: "product" });
    char_field = fields.Char();

    _records = [];
}

class Partner extends models.Model {
    display_name = fields.Char();
    image = fields.Binary();
    empty_image = fields.Binary();

    _records = [
        {
            id: 1,
            display_name: "jean",
        },
    ];
}

class Product extends models.Model {
    display_name = fields.Char();

    _records = [{ id: 1, display_name: "A very good product" }];
}

defineModels([Coucou, Product, Partner]);

test("Form editor should contains the view and the editor sidebar", async () => {
    await mountViewEditor({
        type: "form",
        resModel: "coucou",
        arch: `<form>
            <sheet>
                <field name="display_name"/>
            </sheet>
        </form>
        `,
    });
    expect(".o_web_studio_editor_manager .o_web_studio_view_renderer").toHaveCount(1);
    expect(".o_web_studio_editor_manager .o_web_studio_sidebar").toHaveCount(1);
});

test("empty form editor", async () => {
    await mountViewEditor({
        type: "form",
        resModel: "coucou",
        arch: `<form/>
        `,
    });
    expect(".o_web_studio_form_view_editor").toHaveCount(1);
    expect(".o_web_studio_form_view_editor .o-web-studio-editor--element-clickable").toHaveCount(0);
    expect(".o_web_studio_form_view_editor .o_web_studio_hook").toHaveCount(0);
});

test.tags("desktop");
test("Form editor view buttons can be set to invisible", async () => {
    onRpc("/web_studio/edit_view", async (request) => {
        const { params } = await request.json();
        expect(params.operations[0].target.xpath_info).toEqual([
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
        expect(params.operations[0].new_attrs).toEqual({ invisible: "True" });
        expect.step("edit_view");
    });
    await mountViewEditor({
        type: "form",
        resModel: "coucou",
        arch: `<form>
            <header>
                <button string="Test" type="object" class="oe_highlight"/>
            </header>
            <sheet>
                <field name="display_name"/>
            </sheet>
        </form>
        `,
    });
    expect(".o_web_studio_editor_manager .o_web_studio_view_renderer").toHaveCount(1);
    expect(".o_web_studio_editor_manager .o_web_studio_sidebar").toHaveCount(1);
    await contains(".o_form_renderer .o_statusbar_buttons > button").click();
    await contains(".o_notebook #invisible").click();
    expect.verifySteps(["edit_view"]);
});

test.tags("desktop");
test("Form editor view buttons label and class are editable from the sidebar", async () => {
    let count = 0;

    onRpc("/web_studio/edit_view", async (request) => {
        const { params } = await request.json();
        expect(params.operations[0].target.xpath_info).toEqual([
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
        if (count === 0) {
            expect(params.operations[0].new_attrs).toEqual({ string: "MyLabel" });
        } else {
            expect(params.operations[1].new_attrs).toEqual({ class: "btn-secondary" });
        }
        count++;
        expect.step("edit_view");
    });
    await mountViewEditor({
        type: "form",
        resModel: "coucou",
        arch: `<form>
            <header>
                <button string="Test" type="object" class="oe_highlight"/>
            </header>
            <sheet>
                <field name="display_name"/>
            </sheet>
        </form>
        `,
    });
    expect(".o_web_studio_editor_manager .o_web_studio_view_renderer").toHaveCount(1);
    expect(".o_web_studio_editor_manager .o_web_studio_sidebar").toHaveCount(1);
    await contains(".o_form_renderer .o_statusbar_buttons > button").click();
    expect("input[name=string]").toHaveValue("Test");
    await contains("input[name=string]").edit("MyLabel");
    expect.verifySteps(["edit_view"]);
    expect("input[name=class]").toHaveValue("oe_highlight");
    await contains("input[name=class]").edit("btn-secondary");
    expect.verifySteps(["edit_view"]);
});

test("optional field not in form editor", async () => {
    await mountViewEditor({
        type: "form",
        resModel: "coucou",
        arch: `<form>
            <sheet>
                <field name="display_name"/>
            </sheet>
        </form>
        `,
    });
    await contains(".o_web_studio_view_renderer .o_field_char").click();
    expect(".o_web_studio_sidebar_optional_select").toHaveCount(0);
});

test("many2one field edition", async () => {
    onRpc("/web_studio/get_studio_view_arch", () => ({ studio_view_arch: "" }));
    onRpc("get_formview_action", () => {
        throw new Error("The many2one form view should not be opened");
    });
    await mountViewEditor({
        type: "form",
        resModel: "coucou",
        arch: `<form>
            <sheet>
                <field name="m2o"/>
            </sheet>
        </form>
        `,
    });
    expect(".o_web_studio_form_view_editor .o-web-studio-editor--element-clickable").toHaveCount(1);
    await contains(
        ".o_web_studio_form_view_editor .o-web-studio-editor--element-clickable"
    ).click();
    expect(queryAll(".o_web_studio_sidebar .o_web_studio_property").length > 0).toBe(true);
    expect(".o_web_studio_form_view_editor .o-web-studio-editor--element-clickable").toHaveClass(
        "o-web-studio-editor--element-clicked"
    );
});

test("image field is the placeholder when record is empty", async () => {
    await mountViewEditor({
        type: "form",
        resModel: "partner",
        arch: `<form>
            <sheet>
                <field name='empty_image' widget='image'/>
            </sheet>
        </form>
        `,
    });
    expect(".o_web_studio_form_view_editor .o_field_image").toHaveCount(1);
    expect(".o_web_studio_form_view_editor .o_field_image img").toHaveAttribute(
        "data-src",
        "/web/static/img/placeholder.png",
        {
            message: "default image in empty record should be the placeholder",
        }
    );
});

test("image field edition (change size)", async () => {
    onRpc("/web_studio/edit_view", (request) => {
        const newArch = `
                <form>
                    <sheet>
                        <field name='image' widget='image' options='{"size":[0, 270],"preview_image":"coucou"}'/>
                    </sheet>
                </form>
            `;
        return editView(request, "form", newArch);
    });

    patchWithCleanup(ImageField.prototype, {
        setup() {
            super.setup();
            onMounted(() => {
                expect.step(
                    `image, width: ${this.props.width}, height: ${this.props.height}, previewImage: ${this.props.previewImage}`
                );
            });
        },
    });
    await mountViewEditor({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name='image' widget='image' options='{"size":[0, 90],"preview_image":"coucou"}'/>
                </sheet>
            </form>
        `,
    });
    expect(".o_web_studio_form_view_editor .o_field_image").toHaveCount(1);
    // the image should have been fetched
    expect.verifySteps(["image, width: undefined, height: 90, previewImage: coucou"]);
    await contains(".o_web_studio_form_view_editor .o_field_image").click();
    expect(".o_web_studio_property_size").toHaveCount(1);
    expect(".o_web_studio_property_size .text-start").toHaveText("Small");
    expect(".o_web_studio_form_view_editor .o_field_image").toHaveClass(
        "o-web-studio-editor--element-clicked"
    );
    await contains(".o_web_studio_property_size button").click();
    await contains(".o_select_menu_item_label:contains(Large)").click();
    // the image should have been fetched again
    expect.verifySteps(["image, width: undefined, height: 270, previewImage: coucou"]);
    expect(".o_web_studio_property_size .text-start").toHaveText("Large");
});

test("image size can be unset from the selection", async () => {
    let editViewCount = 0;

    onRpc("/web_studio/edit_view", (request) => {
        editViewCount++;
        let newArch;
        if (editViewCount === 1) {
            newArch = `<form>
                <sheet>
                    <field name='image' widget='image' class='oe_avatar' options='{"preview_image": "image"}'/>
                    <div class='oe_title'>
                        <field name='display_name'/>
                    </div>
                </sheet>
            </form>`;
        }
        return editView(request, "form", newArch);
    });

    await mountViewEditor({
        type: "form",
        resModel: "partner",
        arch: `<form>
            <sheet>
                <field name='image' widget='image' class='oe_avatar' options='{"preview_image": "image", "size": [0,90]}'/>
                <div class='oe_title'>
                    <field name='display_name'/>
                </div>
            </sheet>
        </form>`,
    });
    expect('.o_field_widget.oe_avatar[name="image"]').toHaveCount(1);
    await contains(".o_field_widget[name='image']").click();
    expect(".o_web_studio_property_size .text-start").toHaveText("Small");
    await contains(".o_web_studio_property_size .o_select_menu_toggler_clear").click();
    expect(".o_web_studio_property_size .o_select_menu").toHaveText("");
});

test("signature field edition (change full_name)", async () => {
    let editViewCount = 0;
    let newFieldName;

    onRpc("/web_studio/edit_view", async (request) => {
        const { params } = await request.json();
        editViewCount++;
        let newArch;
        if (editViewCount === 1) {
            expect(params.operations[0].node.attrs.widget).toBe("signature", {
                message: "'signature' widget should be there on field being dropped",
            });
            newFieldName = params.operations[0].node.field_description.name;
            newArch = `
                <form>
                    <group>
                        <field name='display_name'/>
                        <field name='m2o'/>
                        <field name='${newFieldName}' widget='signature'/>
                    </group>
                </form>
                `;
            Coucou._fields[newFieldName] = fields.Binary({
                string: "Signature",
            });
            return editView(params, "form", newArch);
        } else if (editViewCount === 2) {
            expect(params.operations[1].new_attrs.options).toBe('{"full_name":"display_name"}', {
                message: "correct options for 'signature' widget should be passed",
            });
            newArch = `
                <form>
                    <group>
                        <field name='display_name'/>
                        <field name='m2o'/>
                        <field name='${newFieldName}' widget='signature' options='{"full_name": "display_name"}'/>
                    </group>
                </form>
                `;
        } else if (editViewCount === 3) {
            expect(params.operations[2].new_attrs.options).toBe('{"full_name":"m2o"}', {
                message: "correct options for 'signature' widget should be passed",
            });
            newArch = `
                <form>
                    <group>
                        <field name='display_name'/>
                        <field name='m2o'/>
                        <field name='${newFieldName}' widget='signature' options='{"full_name": "m2o"}'/>
                    </group>
                </form>
                `;
        }
        return editView(params, "form", newArch);
    });
    await mountViewEditor({
        type: "form",
        resModel: "coucou",
        arch: `
            <form>
                <group>
                    <field name='display_name'/>
                    <field name='m2o'/>
                </group>
            </form>
        `,
    });
    await contains(".o_web_studio_new_fields .o_web_studio_field_signature").dragAndDrop(
        ".o_inner_group .o_web_studio_hook:first-child"
    );
    expect(".o_web_studio_form_view_editor .o_signature").toHaveCount(1);
    await contains(".o_web_studio_form_view_editor .o_signature").click();
    expect(".o_web_studio_property_full_name .o-dropdown").toHaveCount(1);
    expect(".o_web_studio_property_full_name button").toHaveText("", {
        message: "the auto complete field should be empty by default",
    });
    await contains(".o_web_studio_property_full_name button").click();
    await contains(".o_select_menu_item_label:contains(Name)").click();
    expect(".o_web_studio_property_full_name button").toHaveText("Display name");
    await contains(".o_web_studio_property_full_name button").click();
    await contains(".o_select_menu_item_label:contains(Product)").click();
    expect(".o_web_studio_property_full_name button").toHaveText("Product");
});

test("integer field should come with 0 as default value", async () => {
    onRpc("/web_studio/edit_view", async (request) => {
        const { params } = await request.json();
        expect.step("edit_view");
        expect(params.operations[0].node.field_description.type).toBe("integer");
        expect(params.operations[0].node.field_description.default_value).toBe("0");
    });

    await mountViewEditor({
        type: "form",
        resModel: "coucou",
        arch: `
            <form>
                <group>
                    <field name='display_name'/>
                </group>
            </form>`,
    });
    await contains(".o_web_studio_new_fields .o_web_studio_field_integer").dragAndDrop(
        ".o_web_studio_hook[data-position=before]"
    );
    expect.verifySteps(["edit_view"]);
});

test("daterange field should validate {start,end}_date_field", async () => {
    Partner._fields.datetime_start = fields.Datetime({ string: "Start date" });
    Partner._fields.datetime_end = fields.Datetime({ string: "End date" });
    Partner._fields.datetime_other = fields.Datetime({ string: "Other date" });

    const { env } = await mountViewEditor({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <group>
                    <field name="datetime_start" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
                </group>
            </form>`,
    });

    patchWithCleanup(env.services.dialog, {
        add(component, props) {
            expect(props.body).toBe(
                "You can't select the 'Start date field' and 'End date field' at the same time"
            );
            expect.step("error-dialog");
        },
    });

    await contains(".o_form_label").click();
    await contains(".o_web_studio_property_start_date_field .o_select_menu_toggler").click();
    await contains(".o_popover .o_select_menu_item_label:contains('Other date')").click();
    expect.verifySteps(["error-dialog"]);
});

test("supports multiple occurences of field", async () => {
    await mountViewEditor({
        type: "form",
        resModel: "coucou",
        arch: `<form><group>
                <field name="display_name" widget="phone" options="{'enable_sms': false}" />
                <field name="display_name" invisible="1" />
            </group></form>`,
    });
    expect(
        ".o_web_studio_form_view_editor .o_inner_group .o-web-studio-editor--element-clickable"
    ).toHaveCount(1);
    await contains(".o_web_studio_sidebar .o_notebook_headers .nav-link:contains(View)").click();
    await contains(".o_web_studio_sidebar #show_invisible").click();
    expect(
        ".o_web_studio_form_view_editor .o_inner_group .o-web-studio-editor--element-clickable"
    ).toHaveCount(2);
    await contains(
        ".o_web_studio_form_view_editor .o_wrap_field:nth-child(2) .o-web-studio-editor--element-clickable"
    ).click();
    // Would be true if not present in node's options
    expect(".o_web_studio_sidebar input[name='enable_sms']").not.toBeChecked();
    await contains(
        ".o_web_studio_form_view_editor .o_wrap_field:nth-child(3) .o-web-studio-editor--element-clickable"
    ).click();
    expect(".o_web_studio_sidebar input[name='invisible']").toBeChecked();
});

test("options with computed display to have a dynamic sidebar list of options", async () => {
    let editCount = 0;
    // For this test, create fake options and make them tied to each other,
    // so the display and visibility is adapted in the editor sidebar
    patchWithCleanup(charField, {
        supportedOptions: [
            {
                label: "Fake super option",
                name: "fake_super_option",
                type: "boolean",
            },
            {
                label: "Suboption A",
                name: "suboption_a",
                type: "string",
            },
            {
                label: "Suboption B",
                name: "suboption_b",
                type: "boolean",
            },
            {
                label: "Suboption C",
                name: "suboption_c",
                type: "selection",
                choices: [
                    { label: "September 13", value: "sep_13" },
                    { label: "September 23", value: "sep_23" },
                ],
                default: "sep_23",
            },
            {
                label: "Suboption D",
                name: "suboption_d",
                type: "boolean",
            },
        ],
    });
    patchWithCleanup(COMPUTED_DISPLAY_OPTIONS, {
        suboption_a: {
            superOption: "fake_super_option",
            getInvisible: (value) => !value,
        },
        suboption_b: {
            superOption: "suboption_a",
            getReadonly: (value) => !value,
        },
        suboption_c: {
            superOption: "suboption_a",
            getInvisible: (value) => !value,
        },
        suboption_d: {
            superOption: "suboption_b",
            getValue: (value) => value,
            getReadonly: (value) => value,
        },
    });

    const arch = `<form><group>
        <field name="display_name"/>
    </group></form>`;
    onRpc("/web_studio/edit_view", (request) => {
        editCount++;
        if (editCount === 1) {
            const newArch =
                "<form><group><field name='display_name' options='{\"fake_super_option\":True}'/></group></form>";
            return editView(request, "form", newArch);
        }
        if (editCount === 2) {
            const newArch = `<form><group><field name='display_name' options="{'fake_super_option':True,'suboption_a':'Nice'}"/></group></form>`;
            return editView(request, "form", newArch);
        }
        if (editCount === 3) {
            const newArch = `<form><group><field name='display_name' options="{'fake_super_option':True,'suboption_a':'Nice','suboption_b':True}"/></group></form>`;
            return editView(request, "form", newArch);
        }
    });
    await mountViewEditor({
        type: "form",
        resModel: "coucou",
        arch,
    });

    await contains(".o_cell[data-field-name=display_name]").click();
    expect(".o_web_studio_property").toHaveCount(10);
    await contains("input[id=fake_super_option]").check();
    expect(".o_web_studio_property").toHaveCount(13);
    expect(".o_web_studio_property input[id='suboption_b']").not.toBeEnabled();
    expect(".o_web_studio_property input[id='suboption_d']").toBeEnabled();
    expect(".o_web_studio_property input[id='suboption_d']").not.toBeChecked();
    await contains("input[id=suboption_a]").edit("Nice");
    expect(".o_web_studio_property").toHaveCount(14);
    await contains("input[id=suboption_b]").check();
    expect(".o_web_studio_property").toHaveCount(14);
    expect(".o_web_studio_property input[id='suboption_d']").not.toBeEnabled();
    expect(".o_web_studio_property input[id='suboption_d']").toBeChecked();
    const computedOptions = queryAll(
        ".o_web_studio_property:nth-child(n+10):nth-last-child(n+5) label"
    );
    expect([...computedOptions].map((label) => label.textContent).join(", ")).toBe(
        "Suboption A, Suboption B, Suboption D, Suboption C",
        {
            message: "options are ordered and grouped with the corresponding super option",
        }
    );
});

test("field selection when editing a suboption", async () => {
    let editCount = 0;
    patchWithCleanup(charField, {
        supportedOptions: [
            {
                label: "Fake super option",
                name: "fake_super_option",
                type: "boolean",
            },
            {
                label: "Suboption",
                name: "suboption",
                type: "field",
            },
        ],
    });
    patchWithCleanup(COMPUTED_DISPLAY_OPTIONS, {
        suboption: {
            superOption: "fake_super_option",
            getInvisible: (value) => !value,
        },
    });

    const arch = `<form><group>
        <field name="display_name"/>
    </group></form>`;
    onRpc("/web_studio/edit_view", (request) => {
        editCount++;
        if (editCount === 1) {
            const newArch =
                "<form><group><field name='display_name' options='{\"fake_super_option\":True}'/></group></form>";
            return editView(request, "form", newArch);
        }
    });
    await mountViewEditor({
        type: "form",
        resModel: "coucou",
        arch,
    });

    await contains(".o_cell[data-field-name=display_name]").click();
    expect(".o_web_studio_property").toHaveCount(10);
    await contains("input[id=fake_super_option]").check();
    expect(".o_web_studio_property").toHaveCount(11);
    expect(".o_web_studio_property_suboption .o_select_menu").toHaveCount(1);
});

test("option of type 'string' are correctly saved and displayed", async () => {
    patchWithCleanup(charField, {
        supportedOptions: [
            {
                label: "Suboption A",
                name: "suboption_a",
                type: "string",
            },
        ],
    });

    onRpc("/web_studio/edit_view", async (request) => {
        const { params } = await request.json();
        expect(params.operations[0].type).toBe("attributes");
        expect(params.operations[0].new_attrs).toEqual({
            options: JSON.stringify({ suboption_a: "overriden" }),
        });

        const newArch =
            "<form><group><field name='display_name' options='{\"suboption_a\": \"Noice\"}'/></group></form>";
        return editView(request, "form", newArch);
    });

    const arch = `<form><group>
        <field name="display_name" options='{\"suboption_a\": \"cool cool\"}'/>
    </group></form>`;
    await mountViewEditor({
        type: "form",
        resModel: "coucou",
        arch,
    });
    await contains('.o_cell:has([name="display_name"])').click();
    await waitFor("input[id=suboption_a]:value(cool cool)");
    expect("input[id=suboption_a]").toHaveValue("cool cool");
    await contains("input[id=suboption_a]").edit("overriden"); // value overriden in route to make the assert relevant
    await waitFor("input[id=suboption_a]:value(Noice)");
    expect("input[id=suboption_a]").toHaveValue("Noice");
});

test.tags("desktop");
test("'class' attribute is editable in the sidebar with a tooltip", async () => {
    const arch = `<form>
        <header>
            <button string="Test" type="object" class="oe_highlight"/>
        </header>
        <sheet>
            <field name="display_name" class="studio"/>
        </sheet>
    </form>
    `;
    onRpc("/web_studio/edit_view", async (request) => {
        const { params } = await request.json();
        expect(params.operations[0].new_attrs).toEqual({ class: "new_class" });
        return editView(params, "form", arch);
    });
    await mountViewEditor({
        type: "form",
        resModel: "coucou",
        arch,
    });
    await contains(".o_field_char").click();
    expect(".o_web_studio_property input[id=class]").toHaveCount(1);
    expect(".o_web_studio_property input[id=class]").toHaveValue("studio");
    const tooltip =
        "Use Bootstrap or any other custom classes to customize the style and the display of the element.";
    expect(".o_web_studio_property label:contains(Class) sup").toHaveAttribute(
        "data-tooltip",
        tooltip
    );
    await contains(".o_web_studio_property input[id=class]").edit("new_class");
    await contains(".o_statusbar_buttons button").click();
    expect(".o_web_studio_property input[id=class]").toHaveCount(1);
    expect(".o_web_studio_property input[id=class]").toHaveValue("oe_highlight");
    expect(".o_web_studio_property label:contains(Class) sup").toHaveAttribute(
        "data-tooltip",
        tooltip
    );
});

test.tags("desktop");
test("the name of the selected element is displayed in the sidebar", async () => {
    await mountViewEditor({
        type: "form",
        resModel: "coucou",
        arch: `<form>
        <header>
            <button string="Test" type="object" class="oe_highlight"/>
        </header>
        <sheet>
            <group>
                <field name="display_name" class="studio"/>
                <field name="m2o"/>
            </group>
            <notebook>
                <page string="Notes"/>
            </notebook>
        </sheet>
    </form>
    `,
    });
    await contains(".o_inner_group").click();
    expect(".o_web_studio_sidebar h3").toHaveText("Column");
    await contains(".o_cell[data-field-name=display_name]").click();
    expect(".o_web_studio_sidebar h3").toHaveText("Field");
    expect(".o_web_studio_sidebar h3").toHaveClass("o_web_studio_field_char", {
        message: "type of the field is displayed with an icon",
    });
    await contains(".o_cell[data-field-name=m2o]").click();
    expect(".o_web_studio_sidebar h3").toHaveClass("o_web_studio_field_many2one");
    await contains(".o_statusbar_buttons button").click();
    expect(".o_web_studio_sidebar h3.o_web_studio_icon_container").toHaveText("Button");
    await contains(".nav-link:contains(Notes)").click();
    expect(".o_web_studio_sidebar h3.o_web_studio_icon_container").toHaveText("Page");
});

test("edit options and attributes on a widget node", async () => {
    let editCount = 0;

    class MyTestWidget extends Component {
        static template = xml`<div t-attf-class="bg-{{props.color}}" t-attf-style="width:{{props.width}}px;">Inspector widget</div>`;
        static props = ["*"];
    }
    registry.category("view_widgets").add("test_widget", {
        component: MyTestWidget,
        extractProps: ({ attrs, options }) => ({
            width: attrs.width,
            color: options.color,
        }),
        supportedAttributes: [
            {
                label: "Width",
                name: "width",
                type: "string",
            },
        ],
        supportedOptions: [
            {
                label: "Color option",
                name: "color",
                type: "string",
            },
        ],
    });

    const arch = `<form><group>
        <widget name="test_widget"/>
    </group></form>`;
    onRpc("/web_studio/edit_view", async (request) => {
        const { params } = await request.json();
        editCount++;
        if (editCount === 1) {
            const newArch = `<form><group>
                <widget name="test_widget" width="30"/>
            </group></form>`;
            expect(params.operations[0].new_attrs).toEqual({ width: "30" });
            return editView(params, "form", newArch);
        }
        if (editCount === 2) {
            expect(params.operations[1].new_attrs).toEqual({ options: '{"color":"primary"}' });
            const newArch = `<form><group>
                <widget name="test_widget" width="30" options="{'color': 'primary'}"/>
            </group></form>`;
            return editView(params, "form", newArch);
        }
    });
    await mountViewEditor({
        type: "form",
        resModel: "coucou",
        arch,
    });

    await contains(".o_widget_test_widget").click();
    expect(".o_web_studio_property").toHaveCount(3);
    await contains("input[id=width]").edit("30");
    expect(".o_widget_test_widget div").toHaveStyle({ width: "30px" });
    await contains(".o_widget_test_widget").click();
    await contains("input[id=color]").edit("primary");
    expect(".o_widget_test_widget div").toHaveClass("bg-primary");
});

test("never save record -- hiding tab", async () => {
    const steps = [];
    onRpc("web_save", () => {
        steps.push("web_save");
    });
    patchWithCleanup(formEditor, {
        props() {
            const props = super.props(...arguments);
            class TestModel extends props.Model {}
            TestModel.Record = class extends TestModel.Record {
                _save() {
                    steps.push("_save");
                    return super._save(...arguments);
                }
            };
            props.Model = TestModel;
            return props;
        },
    });
    const arch = `<form><field name="display_name"/></form>`;
    await mountViewEditor({
        type: "form",
        resModel: "coucou",
        arch,
    });

    const visibilityStateProp = Object.getOwnPropertyDescriptor(
        Document.prototype,
        "visibilityState"
    );
    const prevVisibilitySate = document.visibilityState;
    Object.defineProperty(document, "visibilityState", {
        value: "hidden",
        configurable: true,
        writable: true,
    });

    document.dispatchEvent(new Event("visibilitychange"));
    await animationFrame();
    expect(steps).toEqual(["_save"]);
    Object.defineProperty(document, "visibilityState", visibilityStateProp);
    expect(document.visibilityState).toBe(prevVisibilitySate);
});

test("CharField can edit its placeholder_field option", async () => {
    await mountViewEditor({
        type: "form",
        resModel: "coucou",
        arch: `<form>
        <header>
            <button string="Test" type="object" class="oe_highlight"/>
        </header>
        <sheet>
            <group>
                <field name="display_name" class="studio"/>
            </group>
        </sheet>
    </form>
    `,
    });
    await contains(".o_cell[data-field-name=display_name]").click();
    expect(".o_web_studio_property[name=placeholder_field]").toHaveCount(1);
    expect(".o_web_studio_property label[for=placeholder_field]").toHaveText(
        "Dynamic Placeholder?",
        {
            message: "the option is title Dynamic Placeholder and has a tooltip",
        }
    );
    expect(".o_web_studio_property[name=dynamic_placeholder]").toHaveCount(0, {
        message:
            "this options is not documented, because it does not make sense to edit this from studio",
    });
    expect(".o_web_studio_property[name=dynamic_placeholder_model_reference_field]").toHaveCount(
        0,
        {
            message:
                "this options is not documented, because it does not make sense to edit this from studio",
        }
    );
});

test("always invisible fields are flagged as not present in arch", async () => {
    await mountViewEditor({
        type: "form",
        resModel: "coucou",
        arch: `<form>
            <field name="display_name" />
            <field name="m2o" invisible="True" />
            <field name="char_field" invisible="1" />
        </form>
    `,
    });

    expect(".o_web_studio_view_renderer .o_field_widget").toHaveCount(1);
    await contains(".o_web_studio_sidebar .o_web_studio_existing_fields_header").click();
    expect(".o_web_studio_sidebar .o_web_studio_existing_fields").toHaveText(
        "Product\nChar field\nId\nLast Modified on\nCreated on"
    );
});
