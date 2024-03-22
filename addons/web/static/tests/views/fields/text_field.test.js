import { expect, test } from "@odoo/hoot";
import { press, queryAll, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    fieldInput,
    fields,
    makeMockServer,
    models,
    mountView,
    onRpc,
} from "../../web_test_helpers";

function fieldTextArea(name) {
    return contains(`.o_field_widget[name='${name}'] textarea`);
}

class Product extends models.Model {
    description = fields.Text();
}

defineModels([Product]);

onRpc("has_group", () => true);

test("basic rendering", async () => {
    Product._records = [{ id: 1, description: "Description as text" }];
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: '<form><field name="description"/></form>',
    });
    expect(".o_field_text textarea").toHaveCount(1);
    expect(".o_field_text textarea").toHaveValue("Description as text");
});

test("doesn't have a scrollbar with long content", async () => {
    Product._records = [{ id: 1, description: "L\no\nn\ng\nD\ne\ns\nc\nr\ni\np\nt\ni\no\nn\n" }];
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: '<form><field name="description"/></form>',
    });
    const textarea = queryOne(".o_field_text textarea");
    expect(textarea.clientHeight).toBe(textarea.scrollHeight);
});

test("render following an onchange", async () => {
    Product._fields.name = fields.Char({
        onChange: (record) => {
            expect.step("onchange");
            record.description = "Content ".repeat(100); // long text
        },
    });
    Product._records = [{ id: 1, description: "Description as text" }];
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: `<form><field name="description"/><field name="name"/></form>`,
    });
    const textarea = queryOne(".o_field_text textarea");
    const initialHeight = textarea.offsetHeight;
    await fieldInput("name").edit("Let's trigger the onchange");
    await animationFrame();
    expect(textarea.offsetHeight).toBeGreaterThan(initialHeight);
    await fieldTextArea("description").edit("Description as text");
    expect(textarea.offsetHeight).toBe(initialHeight);
    expect(textarea.clientHeight).toBe(textarea.scrollHeight);
    expect(["onchange"]).toVerifySteps();
});

test("no scroll bar in editable list", async () => {
    Product._records = [{ id: 1, description: "L\no\nn\ng\nD\ne\ns\nc\nr\ni\np\nt\ni\no\nn\n" }];
    await mountView({
        type: "list",
        resModel: "product",
        arch: '<list editable="top"><field name="description"/></list>',
    });
    await contains(".o_data_row .o_data_cell").click();
    const textarea = queryOne(".o_field_text textarea");
    expect(textarea.clientHeight).toBe(textarea.scrollHeight);
    await contains("tr:not(.o_data_row)").click();
    const cell = queryOne(".o_data_row .o_data_cell");
    expect(cell.clientHeight).toBe(cell.scrollHeight);
});

test("set row on text fields", async () => {
    Product._records = [{ id: 1, description: "Description as text" }];
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: `<form><field name="description" rows="40"/><field name="description"/></form>`,
    });
    const textareas = queryAll(".o_field_text textarea");
    expect(textareas[0].rows).toBe(40);
    expect(textareas[0].clientHeight).toBeGreaterThan(textareas[1].clientHeight);
});

test("is translatable", async () => {
    Product._fields.description = fields.Text({ translate: true });
    Product._records = [{ id: 1, description: "Description as text" }];
    await makeMockServer({
        multi_lang: true,
    });
    onRpc("get_installed", () => [
        ["en_US", "English"],
        ["fr_BE", "French (Belgium)"],
    ]);
    onRpc("get_field_translations", () => [
        [
            { lang: "en_US", source: "Description as text", value: "Description as text" },
            {
                lang: "fr_BE",
                source: "Description as text",
                value: "Description sous forme de texte",
            },
        ],
        { translation_type: "text", translation_show_source: false },
    ]);
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: `<form><sheet><group><field name="description"/></group></sheet></form>`,
    });
    expect(".o_field_text textarea").toHaveClass("o_field_translate");
    expect(".o_field_text .btn.o_field_translate").toHaveCount(1);
    await contains(".o_field_text .btn.o_field_translate").click();
    expect(".modal").toHaveCount(1);
});

test("is translatable on new record", async () => {
    Product._fields.description = fields.Text({ translate: true });
    Product._records = [{ id: 1, description: "Description as text" }];
    await makeMockServer({
        multi_lang: true,
    });
    await mountView({
        type: "form",
        resModel: "product",
        arch: `<form><sheet><group><field name="description"/></group></sheet></form>`,
    });
    expect(".o_field_text .btn.o_field_translate").toHaveCount(1);
});

test("press enter inside editable list", async () => {
    Product._records = [{ id: 1, description: "Description as text" }];
    await mountView({
        type: "list",
        resModel: "product",
        arch: `
            <list editable="top">
                <field name="description" />
            </list>`,
    });
    await contains(".o_data_row .o_data_cell").click();
    expect("textarea.o_input").toHaveCount(1);
    expect("textarea.o_input").toHaveValue("Description as text");
    expect("textarea.o_input").toBeFocused();
    expect("textarea.o_input").toHaveValue("Description as text");
    await fieldTextArea("description").press("Enter");
    expect("textarea.o_input").toHaveValue("Description as text\n");
    expect("textarea.o_input").toBeFocused();
    expect("tr.o_data_row").toHaveCount(1);
});

test("in editable list view", async () => {
    Product._records = [{ id: 1, description: "Description as text" }];
    await mountView({
        type: "list",
        resModel: "product",
        arch: '<tree editable="top"><field name="description"/></tree>',
    });
    await contains(".o_list_button_add").click();
    expect("textarea").toBeFocused();
});

test.tags("desktop")("with dynamic placeholder", async () => {
    Product._fields.placeholder = fields.Char({ default: "product" });
    await mountView({
        type: "form",
        resModel: "product",
        arch: `
            <form>
                <field name="placeholder" invisible="1"/>
                <sheet>
                    <group>
                        <field
                            name="description"
                            options="{
                                'dynamic_placeholder': true,
                                'dynamic_placeholder_model_reference_field': 'placeholder'
                            }"
                        />
                    </group>
                </sheet>
            </form>`,
    });
    expect(".o_popover .o_model_field_selector_popover").toHaveCount(0);
    await press("alt+#");
    await animationFrame();
    expect(".o_popover .o_model_field_selector_popover").toHaveCount(1);
});

test.tags("mobile")("with dynamic placeholder in mobile", async () => {
    Product._fields.placeholder = fields.Char({ default: "product" });
    await mountView({
        type: "form",
        resModel: "product",
        arch: `
            <form>
                <field name="placeholder" invisible="1"/>
                <sheet>
                    <group>
                        <field
                            name="description"
                            options="{
                                'dynamic_placeholder': true,
                                'dynamic_placeholder_model_reference_field': 'placeholder'
                            }"
                        />
                    </group>
                </sheet>
            </form>`,
    });
    expect(".o_popover .o_model_field_selector_popover").toHaveCount(0);
    await fieldTextArea("description").focus();
    await press("alt+#");
    await animationFrame();
    expect(".o_popover .o_model_field_selector_popover").toHaveCount(1);
});
