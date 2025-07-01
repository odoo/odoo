import { expect, test } from "@odoo/hoot";
import { queryAll, queryFirst } from "@odoo/hoot-dom";
import { Deferred, animationFrame } from "@odoo/hoot-mock";
import {
    clickSave,
    contains,
    defineModels,
    fieldInput,
    fields,
    models,
    mountView,
    onRpc,
    serverState,
} from "@web/../tests/web_test_helpers";

class Currency extends models.Model {
    digits = fields.Integer();
    symbol = fields.Char({ string: "Currency Symbol" });
    position = fields.Char({ string: "Currency Position" });

    _records = [
        {
            id: 1,
            display_name: "$",
            symbol: "$",
            position: "before",
        },
        {
            id: 2,
            display_name: "€",
            symbol: "€",
            position: "after",
        },
    ];
}

class Partner extends models.Model {
    _name = "res.partner";
    _inherit = [];

    name = fields.Char({
        string: "Name",
        default: "My little Name Value",
        trim: true,
    });
    int_field = fields.Integer();
    partner_ids = fields.One2many({
        string: "one2many field",
        relation: "res.partner",
    });
    product_id = fields.Many2one({ relation: "product" });

    placeholder_name = fields.Char();

    _records = [
        {
            id: 1,
            display_name: "first record",
            name: "yop",
            int_field: 10,
            partner_ids: [],
            placeholder_name: "Placeholder Name",
        },
        {
            id: 2,
            display_name: "second record",
            name: "blip",
            int_field: 0,
            partner_ids: [],
        },
        { id: 3, name: "gnap", int_field: 80 },
        {
            id: 4,
            display_name: "aaa",
            name: "abc",
        },
        { id: 5, name: "blop", int_field: -4 },
    ];

    _views = {
        form: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="name"/>
                    </group>
                </sheet>
            </form>
        `,
    };
}

class PartnerType extends models.Model {
    color = fields.Integer({ string: "Color index" });
    name = fields.Char({ string: "Partner Type" });

    _records = [
        { id: 12, display_name: "gold", color: 2 },
        { id: 14, display_name: "silver", color: 5 },
    ];
}

class Product extends models.Model {
    name = fields.Char({ string: "Product Name" });

    _records = [
        {
            id: 37,
            name: "xphone",
        },
        {
            id: 41,
            name: "xpad",
        },
    ];
}

class Users extends models.Model {
    _name = "res.users";

    name = fields.Char();

    has_group() {
        return true;
    }

    _records = [
        {
            id: 1,
            name: "Aline",
        },
        {
            id: 2,
            name: "Christine",
        },
    ];
}

defineModels([Currency, Partner, PartnerType, Product, Users]);

test("char field in form view", async () => {
    await mountView({ type: "form", resModel: "res.partner", resId: 1 });

    expect(".o_field_widget input[type='text']").toHaveCount(1, {
        message: "should have an input for the char field",
    });
    expect(".o_field_widget input[type='text']").toHaveValue("yop", {
        message: "input should contain field value in edit mode",
    });
    await fieldInput("name").edit("limbo");
    await clickSave();
    expect(".o_field_widget input[type='text']").toHaveValue("limbo", {
        message: "the new value should be displayed",
    });
});

test("setting a char field to empty string is saved as a false value", async () => {
    expect.assertions(1);

    await mountView({ type: "form", resModel: "res.partner", resId: 1 });

    onRpc("web_save", ({ args }) => {
        expect(args[1].name).toBe(false);
    });
    await fieldInput("name").clear();
    await clickSave();
});

test("char field with size attribute", async () => {
    Partner._fields.name.size = 5;
    await mountView({ type: "form", resModel: "res.partner", resId: 1 });

    expect("input").toHaveAttribute("maxlength", "5", {
        message: "maxlength attribute should have been set correctly on the input",
    });
});

test.tags("desktop");
test("char field in editable list view", async () => {
    await mountView({
        type: "list",
        resModel: "res.partner",
        arch: `
            <list editable="bottom">
                <field name="name" />
            </list>`,
    });

    expect("tbody td:not(.o_list_record_selector)").toHaveCount(5, {
        message: "should have 5 cells",
    });
    expect("tbody td:not(.o_list_record_selector):first").toHaveText("yop", {
        message: "value should be displayed properly as text",
    });

    const cellSelector = "tbody td:not(.o_list_record_selector)";
    await contains(cellSelector).click();
    expect(queryFirst(cellSelector).parentElement).toHaveClass("o_selected_row", {
        message: "should be set as edit mode",
    });
    expect(`${cellSelector} input`).toHaveValue("yop", {
        message: "should have the corect value in internal input",
    });
    await fieldInput("name").edit("brolo", { confirm: false });

    await contains(".o_list_button_save").click();
    expect(cellSelector).not.toHaveClass("o_selected_row", {
        message: "should not be in edit mode anymore",
    });
});

test("char field translatable", async () => {
    Partner._fields.name.translate = true;

    serverState.lang = "en_US";
    serverState.multiLang = true;

    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: 1,
    });

    let callGetFieldTranslations = 0;
    onRpc("res.lang", "get_installed", () => [
        ["en_US", "English"],
        ["fr_BE", "French (Belgium)"],
        ["es_ES", "Spanish"],
    ]);
    onRpc("res.partner", "get_field_translations", () => {
        if (callGetFieldTranslations++ === 0) {
            return [
                [
                    { lang: "en_US", source: "yop", value: "yop" },
                    { lang: "fr_BE", source: "yop", value: "yop français" },
                    { lang: "es_ES", source: "yop", value: "yop español" },
                ],
                { translation_type: "char", translation_show_source: false },
            ];
        } else {
            return [
                [
                    { lang: "en_US", source: "bar", value: "bar" },
                    { lang: "fr_BE", source: "bar", value: "yop français" },
                    { lang: "es_ES", source: "bar", value: "bar" },
                ],
                { translation_type: "char", translation_show_source: false },
            ];
        }
    });
    onRpc("res.partner", "update_field_translations", function ({ args, kwargs }) {
        expect(args[2]).toEqual(
            { en_US: "bar", es_ES: false },
            {
                message:
                    "the new translation value should be written and the value false voids the translation",
            }
        );
        for (const record of this.env["res.partner"].browse(args[0])) {
            record[args[1]] = args[2][kwargs.context.lang];
        }
        return true;
    });
    expect("[name=name] input").toHaveClass("o_field_translate");
    await contains("[name=name] input").click();
    expect(".o_field_char .btn.o_field_translate").toHaveCount(1, {
        message: "should have a translate button",
    });
    expect(".o_field_char .btn.o_field_translate").toHaveText("EN", {
        message: "the button should have as test the current language",
    });
    await contains(".o_field_char .btn.o_field_translate").click();
    expect(".modal").toHaveCount(1, {
        message: "a translate modal should be visible",
    });
    expect(".modal .o_translation_dialog .translation").toHaveCount(3, {
        message: "three rows should be visible",
    });
    let translations = queryAll(".modal .o_translation_dialog .translation input");
    expect(translations[0]).toHaveValue("yop", {
        message: "English translation should be filled",
    });
    expect(translations[1]).toHaveValue("yop français", {
        message: "French translation should be filled",
    });
    expect(translations[2]).toHaveValue("yop español", {
        message: "Spanish translation should be filled",
    });
    await contains(translations[0]).edit("bar");
    await contains(translations[2]).clear();
    await contains("footer .btn.btn-primary").click();
    expect(".o_field_widget.o_field_char input").toHaveValue("bar", {
        message: "the new translation should be transfered to modified record",
    });
    await fieldInput("name").edit("baz");
    await contains(".o_field_char .btn.o_field_translate").click();

    translations = queryAll(".modal .o_translation_dialog .translation input");
    expect(translations[0]).toHaveValue("baz", {
        message: "Modified value should be used instead of translation",
    });
    expect(translations[1]).toHaveValue("yop français", {
        message: "French translation shouldn't be changed",
    });
    expect(translations[2]).toHaveValue("bar", {
        message: "Spanish translation should fallback to the English translation",
    });
});

test("translation dialog should close if field is not there anymore", async () => {
    expect.assertions(4);
    // In this test, we simulate the case where the field is removed from the view
    // this can happen for example if the user click the back button of the browser.
    Partner._fields.name.translate = true;

    serverState.lang = "en_US";
    serverState.multiLang = true;

    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: 1,
        arch: `
        <form>
            <sheet>
                <group>
                    <field name="int_field" />
                    <field name="name"  invisible="int_field == 9"/>
                </group>
            </sheet>
        </form>`,
    });
    onRpc(async ({ method, model }) => {
        if (method === "get_installed" && model === "res.lang") {
            return [
                ["en_US", "English"],
                ["fr_BE", "French (Belgium)"],
                ["es_ES", "Spanish"],
            ];
        }
        if (method === "get_field_translations" && model === "res.partner") {
            return [
                [
                    { lang: "en_US", source: "yop", value: "yop" },
                    { lang: "fr_BE", source: "yop", value: "valeur français" },
                    { lang: "es_ES", source: "yop", value: "yop español" },
                ],
                { translation_type: "char", translation_show_source: false },
            ];
        }
    });
    expect("[name=name] input").toHaveClass("o_field_translate");
    await contains("[name=name] input").click();
    await contains(".o_field_char .btn.o_field_translate").click();
    expect(".modal").toHaveCount(1, {
        message: "a translate modal should be visible",
    });
    await fieldInput("int_field").edit("9");
    await animationFrame();
    expect("[name=name] input").toHaveCount(0, {
        message: "the field name should be invisible",
    });
    expect(".modal").toHaveCount(0, {
        message: "a translate modal should not be visible",
    });
});

test("html field translatable", async () => {
    expect.assertions(5);
    Partner._fields.name.translate = true;

    serverState.lang = "en_US";
    serverState.multiLang = true;

    await mountView({ type: "form", resModel: "res.partner", resId: 1 });

    onRpc(async ({ args, method, model }) => {
        if (method === "get_installed" && model === "res.lang") {
            return [
                ["en_US", "English"],
                ["fr_BE", "French (Belgium)"],
            ];
        }
        if (method === "get_field_translations" && model === "res.partner") {
            return [
                [
                    {
                        lang: "en_US",
                        source: "first paragraph",
                        value: "first paragraph",
                    },
                    {
                        lang: "en_US",
                        source: "second paragraph",
                        value: "second paragraph",
                    },
                    {
                        lang: "fr_BE",
                        source: "first paragraph",
                        value: "premier paragraphe",
                    },
                    {
                        lang: "fr_BE",
                        source: "second paragraph",
                        value: "deuxième paragraphe",
                    },
                ],
                {
                    translation_type: "char",
                    translation_show_source: true,
                },
            ];
        }

        if (method === "update_field_translations" && model === "res.partner") {
            expect(args[2]).toEqual(
                { en_US: { "first paragraph": "first paragraph modified" } },
                {
                    message: "the new translation value should be written",
                }
            );
            return true;
        }
    });

    // this will not affect the translate_fields effect until the record is
    // saved but is set for consistency of the test
    await fieldInput("name").edit("<p>first paragraph</p><p>second paragraph</p>");
    await contains(".o_field_char .btn.o_field_translate").click();
    expect(".modal").toHaveCount(1, {
        message: "a translate modal should be visible",
    });
    expect(".modal .o_translation_dialog .translation").toHaveCount(4, {
        message: "four rows should be visible",
    });
    const enField = queryFirst(".modal .o_translation_dialog .translation input");
    expect(enField).toHaveValue("first paragraph", {
        message: "first part of english translation should be filled",
    });
    await contains(enField).edit("first paragraph modified");
    await contains(".modal button.btn-primary").click();
    expect(".o_field_char input[type='text']").toHaveValue(
        "<p>first paragraph</p><p>second paragraph</p>",
        {
            message: "the new partial translation should not be transfered",
        }
    );
});

test("char field translatable in create mode", async () => {
    Partner._fields.name.translate = true;

    serverState.multiLang = true;

    await mountView({ type: "form", resModel: "res.partner" });

    expect(".o_field_char .btn.o_field_translate").toHaveCount(1, {
        message: "should have a translate button in create mode",
    });
});

test("char field does not allow html injections", async () => {
    await mountView({ type: "form", resModel: "res.partner", resId: 1 });
    await fieldInput("name").edit("<script>throw Error();</script>");
    await clickSave();
    expect(".o_field_widget input").toHaveValue("<script>throw Error();</script>", {
        message: "the value should have been properly escaped",
    });
});

test("char field trim (or not) characters", async () => {
    Partner._fields.foo2 = fields.Char({ trim: false });

    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: 1,
        arch: `
        <form>
            <sheet>
                <group>
                    <field name="name" />
                    <field name="foo2" />
                </group>
            </sheet>
        </form>`,
    });

    await fieldInput("name").edit("  abc  ");
    await fieldInput("foo2").edit("  def  ");
    await clickSave();
    expect(".o_field_widget[name='name'] input").toHaveValue("abc", {
        message: "Name value should have been trimmed",
    });
    expect(".o_field_widget[name='foo2'] input:only").toHaveValue("  def  ");
});

test.tags("desktop");
test("input field: change value before pending onchange returns", async () => {
    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: 1,
        arch: `
        <form>
            <sheet>
                <field name="partner_ids">
                    <list editable="bottom">
                        <field name="product_id" />
                        <field name="name" />
                    </list>
                </field>
            </sheet>
        </form>`,
    });

    let def;
    onRpc("onchange", () => def);

    await contains(".o_field_x2many_list_row_add a").click();
    expect(".o_field_widget[name='name'] input").toHaveValue("My little Name Value", {
        message: "should contain the default value",
    });

    def = new Deferred();
    await contains(".o-autocomplete--input").click();
    await contains(".o-autocomplete--dropdown-item").click();
    await fieldInput("name").edit("tralala", { confirm: false });
    expect(".o_field_widget[name='name'] input").toHaveValue("tralala", {
        message: "should contain tralala",
    });
    def.resolve();
    await animationFrame();
    expect(".o_field_widget[name='name'] input").toHaveValue("tralala", {
        message: "should contain the same value as before onchange",
    });
});

test("input field: change value before pending onchange returns (2)", async () => {
    Partner._onChanges.int_field = (obj) => {
        if (obj.int_field === 7) {
            obj.name = "blabla";
        } else {
            obj.name = "tralala";
        }
    };

    const def = new Deferred();
    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: 1,
        arch: `
        <form>
            <sheet>
                <field name="int_field" />
                <field name="name" />
            </sheet>
        </form>`,
    });

    onRpc("onchange", () => def);

    expect(".o_field_widget[name='name'] input").toHaveValue("yop", {
        message: "should contain the correct value",
    });

    // trigger a deferred onchange
    await fieldInput("int_field").edit("7");
    await fieldInput("name").edit("test", { confirm: false });

    def.resolve();
    await animationFrame();
    expect(".o_field_widget[name='name'] input").toHaveValue("test", {
        message: "The onchage value should not be applied because the input is in edition",
    });
    await fieldInput("name").press("Enter");
    await expect(".o_field_widget[name='name'] input").toHaveValue("test");
    await fieldInput("int_field").edit("10");
    await expect(".o_field_widget[name='name'] input").toHaveValue("tralala", {
        message: "The onchange value should be applied because the input is not in edition",
    });
});

test.tags("desktop");
test("input field: change value before pending onchange returns (with fieldDebounce)", async () => {
    // this test is exactly the same as the previous one, except that in
    // this scenario the onchange return *before* we validate the change
    // on the input field (before the "change" event is triggered).
    Partner._onChanges.product_id = (obj) => {
        obj.int_field = obj.product_id ? 7 : false;
    };
    let def;

    await mountView({
        type: "form",
        resModel: "res.partner",
        arch: `
        <form>
            <field name="partner_ids">
                <list editable="bottom">
                    <field name="product_id"/>
                    <field name="name"/>
                    <field name="int_field"/>
                </list>
            </field>
        </form>`,
    });

    onRpc("onchange", () => def);

    await contains(".o_field_x2many_list_row_add a").click();
    expect(".o_field_widget[name='name'] input").toHaveValue("My little Name Value", {
        message: "should contain the default value",
    });

    def = new Deferred();
    await contains(".o-autocomplete--input").click();
    await contains(".o-autocomplete--dropdown-item").click();
    await fieldInput("name").edit("tralala", { confirm: false });
    expect(".o_field_widget[name='name'] input").toHaveValue("tralala", {
        message: "should contain tralala",
    });
    expect(".o_field_widget[name='int_field'] input").toHaveValue("");
    def.resolve();
    await animationFrame();
    expect(".o_field_widget[name='name'] input").toHaveValue("tralala", {
        message: "should contain the same value as before onchange",
    });
    expect(".o_field_widget[name='int_field'] input").toHaveValue("7", {
        message: "should contain the value returned by the onchange",
    });
});

test("onchange return value before editing input", async () => {
    Partner._onChanges.name = (obj) => {
        obj.name = "yop";
    };
    await mountView({ type: "form", resModel: "res.partner", resId: 1 });
    expect(".o_field_widget[name='name'] input").toHaveValue("yop");
    await fieldInput("name").edit("tralala");
    await expect("[name='name'] input").toHaveValue("yop");
});

test.tags("desktop");
test("input field: change value before pending onchange renaming", async () => {
    Partner._onChanges.product_id = (obj) => {
        obj.name = "on change value";
    };

    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: 1,
        arch: `
        <form>
            <sheet>
                <field name="product_id" />
                <field name="name" />
            </sheet>
        </form>`,
    });

    onRpc("onchange", () => def);

    const def = new Deferred();

    expect(".o_field_widget[name='name'] input").toHaveValue("yop", {
        message: "should contain the correct value",
    });
    await contains(".o-autocomplete--input").click();
    await contains(".o-autocomplete--dropdown-item").click();
    // set name before onchange
    await fieldInput("name").edit("tralala");
    await expect(".o_field_widget[name='name'] input").toHaveValue("tralala", {
        message: "should contain tralala",
    });

    // complete the onchange
    def.resolve();
    await animationFrame();
    expect(".o_field_widget[name='name'] input").toHaveValue("tralala", {
        message: "input should contain the same value as before onchange",
    });
});

test("support autocomplete attribute", async () => {
    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: 1,
        arch: `
        <form>
            <field name="name" autocomplete="coucou"/>
        </form>`,
    });
    expect(".o_field_widget[name='name'] input").toHaveAttribute("autocomplete", "coucou", {
        message: "attribute autocomplete should be set",
    });
});

test("input autocomplete attribute set to none by default", async () => {
    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: 1,
        arch: `
        <form>
            <field name="name"/>
        </form>`,
    });
    expect(".o_field_widget[name='name'] input").toHaveAttribute("autocomplete", "off", {
        message: "attribute autocomplete should be set to none by default",
    });
});

test("support password attribute", async () => {
    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: 1,
        arch: `
        <form>
            <field name="name" password="True"/>
        </form>`,
    });
    expect(".o_field_widget[name='name'] input").toHaveValue("yop", {
        message: "input value should be the password",
    });
    expect(".o_field_widget[name='name'] input").toHaveAttribute("type", "password", {
        message: "input should be of type password",
    });
});

test("input field: readonly password", async () => {
    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: 1,
        arch: `
        <form>
            <field name="name" password="True" readonly="1"/>
        </form>`,
    });

    expect(".o_field_char").not.toHaveText("yop", {
        message: "password field value should be visible in read mode",
    });

    expect(".o_field_char").toHaveText("***", {
        message: "password field value should be hidden with '*' in read mode",
    });
});

test("input field: change password value", async () => {
    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: 1,
        arch: `
        <form>
            <field name="name" password="True"/>
        </form>`,
    });

    expect(".o_field_char input").toHaveAttribute("type", "password", {
        message: "password field input value should with type 'password' in edit mode",
    });
    expect(".o_field_char input").toHaveValue("yop", {
        message: "password field input value should be the (hidden) password value",
    });
});

test("input field: empty password", async () => {
    Partner._records[0].name = false;
    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: 1,
        arch: `
        <form>
            <field name="name" password="True"/>
        </form>`,
    });
    expect(".o_field_char input").toHaveAttribute("type", "password", {
        message: "password field input value should with type 'password' in edit mode",
    });
    expect(".o_field_char input").toHaveValue("", {
        message: "password field input value should be the (non-hidden, empty) password value",
    });
});

test.tags("desktop");
test("input field: set and remove value, then wait for onchange", async () => {
    Partner._onChanges.product_id = (obj) => {
        obj.name = obj.product_id ? "onchange value" : false;
    };

    await mountView({
        type: "form",
        resModel: "res.partner",
        arch: `
        <form>
            <field name="partner_ids">
                <list editable="bottom">
                    <field name="product_id"/>
                    <field name="name"/>
                </list>
            </field>
        </form>`,
    });
    await contains(".o_field_x2many_list_row_add a").click();
    expect(".o_field_widget[name=name] input").toHaveValue("");
    await fieldInput("name").edit("test", { confirm: false });
    await fieldInput("name").clear({ confirm: false });

    // trigger the onchange by setting a product
    await contains(".o-autocomplete--input").click();
    await contains(".o-autocomplete--dropdown-item").click();
    expect(".o_field_widget[name=name] input").toHaveValue("onchange value", {
        message: "input should contain correct value after onchange",
    });
});

test("char field with placeholder", async () => {
    Partner._fields.name.default = false;
    await mountView({
        type: "form",
        resModel: "res.partner",
        arch: `
        <form>
            <sheet>
                <group>
                    <field name="name" placeholder="Placeholder" />
                </group>
            </sheet>
        </form>`,
    });
    expect(".o_field_widget[name='name'] input").toHaveAttribute("placeholder", "Placeholder", {
        message: "placeholder attribute should be set",
    });
});

test("Form: placeholder_field shows as placeholder", async () => {
    Partner._records[0].name = false;
    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: 1,
        arch: `
        <form>
            <sheet>
                <group>
                    <field name="placeholder_name" invisible="1" />
                    <field name="name" options="{'placeholder_field': 'placeholder_name'}" />
                </group>
            </sheet>
        </form>`,
    });
    expect("input").toHaveValue("", {
        message: "should have no value in input",
    });
    expect("input").toHaveAttribute("placeholder", "Placeholder Name", {
        message: "placeholder_field should be the placeholder",
    });
});

test("char field: correct value is used to evaluate the modifiers", async () => {
    Partner._records[0].name = false;
    Partner._records[0].display_name = false;
    Partner._onChanges.name = (obj) => {
        if (obj.name === "a") {
            obj.display_name = false;
        } else if (obj.name === "b") {
            obj.display_name = "";
        }
    };
    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: 1,
        arch: `
        <form>
            <field name="name" />
            <field name="display_name" invisible="'' == display_name"/>
        </form>`,
    });
    expect("[name='display_name']").toHaveCount(1);

    await fieldInput("name").edit("a");
    await animationFrame();
    expect("[name='display_name']").toHaveCount(1);

    await fieldInput("name").edit("b");
    await animationFrame();
    expect("[name='display_name']").toHaveCount(0);
});

test("edit a char field should display the status indicator buttons without flickering", async () => {
    Partner._records[0].partner_ids = [2];
    Partner._onChanges.name = (obj) => {
        obj.display_name = "cc";
    };

    const def = new Deferred();
    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: 1,
        arch: `
        <form>
            <field name="partner_ids">
                <list editable="bottom">
                    <field name="name"/>
                </list>
            </field>
        </form>`,
    });
    onRpc("onchange", () => {
        expect.step("onchange");
        return def;
    });
    expect(".o_form_status_indicator_buttons").not.toBeVisible({
        message: "form view is not dirty",
    });
    await contains(".o_data_cell").click();
    await fieldInput("name").edit("a");
    expect(".o_form_status_indicator_buttons").toBeVisible({
        message: "form view is dirty",
    });
    def.resolve();
    expect.verifySteps(["onchange"]);
    await animationFrame();
    expect(".o_form_status_indicator_buttons").toBeVisible({
        message: "form view is dirty",
    });
    expect.verifySteps(["onchange"]);
});
