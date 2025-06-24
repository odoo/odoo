import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { expectElementCount } from "@html_editor/../tests/_helpers/ui_expectations";
import { HtmlMailField } from "@mail/views/web/fields/html_mail_field/html_mail_field";
import { after, before, beforeEach, expect, test } from "@odoo/hoot";
import { press, queryOne } from "@odoo/hoot-dom";
import { animationFrame, enableTransitions } from "@odoo/hoot-mock";
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

function setSelectionInHtmlField(selector = "p", fieldName = "body") {
    const anchorNode = queryOne(`[name='${fieldName}'] .odoo-editor-editable ${selector}`);
    setSelection({ anchorNode, anchorOffset: 0 });
    return anchorNode;
}

function useCustomStyleRules(rules = "") {
    let style;
    before(() => {
        style = document.createElement("STYLE");
        style.type = "text/css";
        style.append(document.createTextNode(rules));
        document.head.append(style);
    });
    after(() => {
        style.remove();
    });
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
        getConfig() {
            const config = super.getConfig();
            config.Plugins = config.Plugins.filter((Plugin) => Plugin.id !== "editorVersion");
            return config;
        },
    });
});

test("HtmlMail save inline html", async function () {
    enableTransitions();
    useCustomStyleRules(`.test-h1-inline .note-editable h1 { color: #111827 !important; }`);
    onRpc("web_save", ({ args }) => {
        expect(args[1].body.replace(/font-size: ?(\d+(\.\d+)?)px/, "font-size: []px")).toBe(
            `<h1 style="border-radius:0px;border-style:none;padding:0px;margin:0px 0 8px 0;box-sizing:border-box;border-left-width:0px;border-bottom-width:0px;border-right-width:0px;border-top-width:0px;font-size: []px;color:#111827;line-height:1.2;font-weight:500;font-family:'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Ubuntu, 'Noto Sans', Arial, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji';">first</h1>`
        );
        expect.step("web_save");
    });
    await mountView({
        type: "form",
        resId: 1,
        resModel: "custom.message",
        arch: `
        <form>
            <field name="body" widget="html_mail" class="test-h1-inline"/>
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
    await expectElementCount(".o-we-powerbox", 1);

    await insertText(htmlEditor, "column");
    await animationFrame();
    await expectElementCount(".o-we-powerbox", 0);
});

test("HtmlMail add icon and save inline html", async function () {
    enableTransitions();
    useCustomStyleRules(
        `.test-icon-inline .note-editable .fa {
            color: rgb(55,65,81) !important;
            background-color: rgb(249,250,251) !important;
        }`
    );
    onRpc("web_save", ({ args }) => {
        expect(args[1].body).toBe(
            `<p style="border-radius:0px;border-style:none;padding:0px;margin:0px 0 16px 0;box-sizing:border-box;border-left-width:0px;border-bottom-width:0px;border-right-width:0px;border-top-width:0px;"><span style="display: inline-block; width: 14px; height: 14px; vertical-align: text-bottom;" class="oe_unbreakable "><img width="14" height="14" src="/web_editor/font_to_img/61440/rgb(55%2C65%2C81)/rgb(249%2C250%2C251)/14x14" data-class="fa fa-glass" data-style="null" style="border-radius:0px;border-style:none;padding:0px;border-left-width:0px;border-bottom-width:0px;border-right-width:0px;border-top-width:0px;box-sizing: border-box; line-height: 14px; width: 14px; height: 14px; vertical-align: unset; margin: 0px;"></span>first</p>`
        );
        expect.step("web_save");
    });
    await mountView({
        type: "form",
        resId: 1,
        resModel: "custom.message",
        arch: `
        <form>
            <field name="body" widget="html_mail" class="test-icon-inline"/>
        </form>`,
    });
    setSelectionInHtmlField();
    await insertText(htmlEditor, "/image");
    await press("enter");

    await contains("a.nav-link:contains('Icons')").click();
    await contains("span.fa-glass").click();

    await contains(".o_form_button_save").click();
    expect.verifySteps(["web_save"]);
});
