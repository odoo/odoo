import { expect, test, waitFor, waitForNone } from "@odoo/hoot";
import { click, edit, pointerDown, queryAll, queryFirst } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    clickSave,
    contains,
    defineModels,
    fields,
    installLanguages,
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
class User extends models.Model {
    _name = "res.users";
    has_group() {
        return true;
    }
}
defineModels([Partner, User]);

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
    expect(queryFirst(".o_notification_content")).toHaveText("Missing required fields");
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
    installLanguages({
        en_US: "American",
        "en-US": "EN",
        fr_BE: "French (Belgium)",
    });

    Partner._fields.txt = fields.Html({ string: "txt", trim: true, translate: true });
    Partner._records.find((r) => r.id === 1).txt = "<p>first paragraph</p><p>second paragraph</p>";

    serverState.lang = "en_US";
    serverState.multiLang = true;

    onRpc("has_group", () => true);

    onRpc("/web/translations/get_translation_for_field", async (request) => {
        const { params } = await request.json();
        expect.step(
            `get_translation_for_field ${params.res_model} - ${params.res_id} - ${params.field_name}`
        );
    });

    onRpc("/web/translations/save_translation_for_field", async (request) => {
        const { params } = await request.json();
        expect.step(params);
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

    await contains(".o_field_html .btn.o_field_translate").click();
    await waitFor(".modal");
    expect.verifySteps(["get_translation_for_field partner - 1 - txt"]);
    expect(".modal").toHaveCount(1, { message: "a translate modal should be visible" });

    await contains(".modal .o-translate-lang-buttons button:contains(French)").click();
    await waitFor(".modal .o-translate-lang-buttons button:contains(French).active");
    expect(".modal .translation").toHaveCount(2, { message: "2 field html present" });

    const translations = queryAll(".modal .o_translation_dialog .translation textarea");
    const enField1 = translations[0];
    expect(enField1).toHaveValue(`<p>first paragraph</p><p>second paragraph</p>`, {
        message: "first part of english translation should be filled",
    });
    await contains(".modal .o_translation_dialog .translation textarea#en_US").edit(
        "first paragraph modified"
    );

    const frField1 = translations[1];
    expect(frField1).toHaveValue(`<p>first paragraph</p><p>second paragraph</p>`, {
        message:
            "first part of french translation should be the same as English because it is not set",
    });
    await contains(".modal .o_translation_dialog .translation textarea#fr_BE").edit(
        "premier paragraphe modifié"
    );
    await contains(".modal footer button.btn-primary:not(disabled)").click(); // save
    await waitForNone(".modal");
    expect.verifySteps([
        {
            changes: {
                en_US: "first paragraph modified",
                fr_BE: "premier paragraphe modifié",
            },
            context: {
                allowed_company_ids: [1],
                lang: "en_US",
                tz: "taht",
                uid: 7,
            },
            field_name: "txt",
            res_id: 1,
            res_model: "partner",
        },
    ]);

    expect("[name=txt] textarea").toHaveValue("first paragraph modified");
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
