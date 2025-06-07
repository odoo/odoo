import { expect, test } from "@odoo/hoot";
import { click, edit, pointerDown, queryAll, queryFirst } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    clickSave,
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    serverState,
} from "@web/../tests/web_test_helpers";

const RED_TEXT = /* html */ `<div class="kek" style="color:red">some text</div>`;
const GREEN_TEXT = /* html */ `<div class="kek" style="color:green">hello</div>`;
const BLUE_TEXT = /* html */ `<div class="kek" style="color:blue">hello world</div>`;

class Partner extends models.Model {
    txt = fields.Html({ string: "txt", trim: true });
    _records = [{ id: 1, txt: RED_TEXT }];
}
defineModels([Partner]);

test("html fields are correctly rendered in form view (readonly)", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `<form><field name="txt" readonly="1" /></form>`,
    });

    expect("div.kek").toHaveCount(1);
    expect(".o_field_html .kek").toHaveStyle({ color: "rgb(255, 0, 0)" });
    expect(".o_field_html").toHaveText("some text");
});

test("html field with required attribute", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `<form><field name="txt" required="1"/></form>`,
    });

    expect(".o_field_html textarea").toHaveCount(1, { message: "should have a text area" });
    await click(".o_field_html textarea");
    await edit("");
    await animationFrame();
    expect(".o_field_html textarea").toHaveValue("");

    await clickSave();
    expect(".o_notification_title").toHaveText("Invalid fields:");
    expect(queryFirst(".o_notification_content")).toHaveInnerHTML("<ul><li>txt</li></ul>");
});

test("html fields are correctly rendered (edit)", async () => {
    onRpc("has_group", () => true);
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `<form><field name="txt" /></form>`,
    });

    expect(".o_field_html textarea").toHaveCount(1, { message: "should have a text area" });
    expect(".o_field_html textarea").toHaveValue(RED_TEXT);
    await click(".o_field_html textarea");
    await edit(GREEN_TEXT);
    await animationFrame();
    expect(".o_field_html textarea").toHaveValue(GREEN_TEXT);
    expect(".o_field_html .kek").toHaveCount(0);

    await edit(BLUE_TEXT);
    await animationFrame();
    expect(".o_field_html textarea").toHaveValue(BLUE_TEXT);
});

test("html fields are correctly rendered in list view", async () => {
    onRpc("has_group", () => true);
    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `<list editable="top"><field name="txt"/></list>`,
    });
    expect(".o_data_row [name='txt']").toHaveText("some text");
    expect(".o_data_row [name='txt'] .kek").toHaveStyle({ color: "rgb(255, 0, 0)" });

    await click(".o_data_row [name='txt']");
    await animationFrame();
    expect(".o_data_row [name='txt'] textarea").toHaveValue(
        '<div class="kek" style="color:red">some text</div>'
    );
});

test("html field displays an empty string for the value false in list view", async () => {
    Partner._records[0].txt = false;
    onRpc("has_group", () => true);

    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `<list editable="top"><field name="txt"/></list>`,
    });

    expect(".o_data_row [name='txt']").toHaveText("");

    await click(".o_data_row [name='txt']");
    await animationFrame();

    expect(".o_data_row [name='txt'] textarea").toHaveValue("");
});

test("html fields are correctly rendered in kanban view", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: /* xml */ `
            <kanban class="o_kanban_test">
                <templates>
                    <t t-name="card">
                        <field name="txt"/>
                    </t>
                </templates>
            </kanban>`,
    });
    expect(".kek").toHaveText("some text");
    expect(".kek").toHaveStyle({ color: "rgb(255, 0, 0)" });
});

test("field html translatable", async () => {
    expect.assertions(10);

    Partner._fields.txt = fields.Html({ string: "txt", trim: true, translate: true });

    serverState.lang = "en_US";
    serverState.multiLang = true;

    onRpc("has_group", () => true);
    onRpc("get_field_translations", function ({ args }) {
        expect(args).toEqual([[1], "txt"], {
            message: "should translate the txt field of the record",
        });
        return [
            [
                { lang: "en_US", source: "first paragraph", value: "first paragraph" },
                {
                    lang: "en_US",
                    source: "second paragraph",
                    value: "second paragraph",
                },
                {
                    lang: "fr_BE",
                    source: "first paragraph",
                    value: "",
                },
                {
                    lang: "fr_BE",
                    source: "second paragraph",
                    value: "deuxième paragraphe",
                },
            ],
            { translation_type: "char", translation_show_source: true },
        ];
    });
    onRpc("get_installed", () => {
        return [
            ["en_US", "English"],
            ["fr_BE", "French (Belgium)"],
        ];
    });
    onRpc("update_field_translations", ({ args }) => {
        expect(args).toEqual(
            [
                [1],
                "txt",
                {
                    en_US: { "first paragraph": "first paragraph modified" },
                    fr_BE: {
                        "first paragraph": "premier paragraphe modifié",
                        "second paragraph": "deuxième paragraphe modifié",
                    },
                },
            ],
            { message: "the new translation value should be written" }
        );
        return [];
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form string="Partner">
                <sheet>
                    <group>
                        <field name="txt" widget="html"/>
                    </group>
                </sheet>
            </form>`,
    });

    expect("[name=txt] textarea").toHaveClass("o_field_translate");
    await contains("[name=txt] textarea").click();
    expect(".o_field_html .btn.o_field_translate").toHaveCount(1, {
        message: "should have a translate button",
    });
    expect(".o_field_html .btn.o_field_translate").toHaveText("EN", {
        message: "the button should have as test the current language",
    });

    await click(".o_field_html .btn.o_field_translate");
    await animationFrame();

    expect(".modal").toHaveCount(1, { message: "a translate modal should be visible" });
    expect(".translation").toHaveCount(4, { message: "four rows should be visible" });

    const translations = queryAll(".modal .o_translation_dialog .translation input");

    const enField1 = translations[0];
    expect(enField1).toHaveValue("first paragraph", {
        message: "first part of english translation should be filled",
    });
    await click(enField1);
    await edit("first paragraph modified");

    const frField1 = translations[2];
    expect(frField1).toHaveValue("", {
        message: "first part of french translation should not be filled",
    });
    await click(frField1);
    await edit("premier paragraphe modifié");

    const frField2 = translations[3];
    expect(frField2).toHaveValue("deuxième paragraphe", {
        message: "second part of french translation should be filled",
    });

    await click(frField2);
    await edit("deuxième paragraphe modifié");

    await click(".modal button.btn-primary"); // save
    await animationFrame();
});

test("html fields: spellcheck is disabled on blur", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `<form><field name="txt" /></form>`,
    });

    const textarea = queryFirst(".o_field_html textarea");
    expect(textarea).toHaveProperty("spellcheck", true, {
        message: "by default, spellcheck is enabled",
    });
    await click(textarea);

    await edit("nev walue");
    await pointerDown(document.body);
    await animationFrame();
    expect(textarea).toHaveProperty("spellcheck", false, {
        message: "spellcheck is disabled once the field has lost its focus",
    });

    await pointerDown(textarea);

    expect(textarea).toHaveProperty("spellcheck", true, {
        message: "spellcheck is re-enabled once the field is focused",
    });
});

test("Setting an html field to empty string is saved as a false value", async () => {
    expect.assertions(1);
    onRpc("web_save", ({ args }) => {
        expect(args[1].txt).toBe(false, { message: "the txt value should be false" });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="txt" />
                    </group>
                </sheet>
            </form>`,
        resId: 1,
    });

    await click(".o_field_widget[name=txt] textarea");
    await edit("");
    await clickSave();
});

test("html field: correct value is used to evaluate the modifiers", async () => {
    Partner._fields.foo = fields.Char({
        string: "foo",
        onChange: (obj) => {
            if (obj.foo === "a") {
                obj.txt = false;
            } else if (obj.foo === "b") {
                obj.txt = "";
            }
        },
    });

    Partner._records[0].foo = false;
    Partner._records[0].txt = false;
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="foo" />
                <field name="txt" invisible="'' == txt"/>
            </form>`,
    });
    expect("[name='txt'] textarea").toHaveCount(1);

    await click("[name='foo'] input");
    await edit("a", { confirm: "enter" });
    await animationFrame();
    expect("[name='txt'] textarea").toHaveCount(1);

    await edit("b", { confirm: "enter" });
    await animationFrame();
    expect("[name='txt'] textarea").toHaveCount(0);
});
