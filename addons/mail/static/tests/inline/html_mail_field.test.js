import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { HtmlMailField } from "@mail/views/web/fields/html_mail_field/html_mail_field";
import { beforeEach, expect, test } from "@odoo/hoot";
import { press, queryOne } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { mailModels } from "../mail_test_helpers";
import { animationFrame } from "@odoo/hoot-mock";

function setSelectionInHtmlField(selector = "p", fieldName = "body") {
    const anchorNode = queryOne(`[name='${fieldName}'] .odoo-editor-editable ${selector}`);
    setSelection({ anchorNode, anchorOffset: 0 });
    return anchorNode;
}

class CustomMessage extends models.Model {
    _name = "custom.message";

    title = fields.Char();
    body = fields.Html();

    _records = [
        { id: 1, title: "first", body: "<p>first</p>" },
        { id: 2, title: "second", body: "<p>second</p>" },
    ];

    _onChanges = {
        title(record) {
            record.body = `<p>${record.title}</p>`;
        },
    };
}

defineModels({ ...mailModels, CustomMessage });

let htmlEditor;
beforeEach(() => {
    patchWithCleanup(HtmlMailField.prototype, {
        onEditorLoad(editor) {
            htmlEditor = editor;
            return super.onEditorLoad(...arguments);
        },
    });
});

test("HtmlMail save inline html", async function () {
    onRpc("web_save", ({ args }) => {
        expect(args[1].body.replace(/font-size: (\d+(\.\d+)?)px/, "font-size: []px")).toBe(
            `<h1 style="margin: 0px 0px 8px; box-sizing: border-box; font-size: []px; line-height: 1.2; font-weight: 500; font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Ubuntu, 'Noto Sans', Arial, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji';">first</h1>`
        );
        expect.step("web_save");
    });
    await mountView({
        type: "form",
        resId: 1,
        resModel: "custom.message",
        arch: `
        <form>
            <field name="body" widget="html_mail"/>
        </form>`,
    });
    setSelectionInHtmlField();
    await insertText(htmlEditor, "/heading1");
    await press("enter");
    expect(".odoo-editor-editable").toHaveInnerHTML("<h1> first </h1>");

    await contains(".o_form_button_save").click();
    expect.verifySteps(["web_save"]);
});

test("HtmlMail don't have access to column commands", async function () {
    await mountView({
        type: "form",
        resId: 1,
        resModel: "custom.message",
        arch: `
        <form>
            <field name="body" widget="html_mail"/>
        </form>`,
    });
    setSelectionInHtmlField();
    await insertText(htmlEditor, "/");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);

    await insertText(htmlEditor, "column");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(0);
});
