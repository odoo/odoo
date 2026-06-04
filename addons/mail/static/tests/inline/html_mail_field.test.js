import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { expectElementCount } from "@html_editor/../tests/_helpers/ui_expectations";
import { HtmlMailField } from "@mail/views/web/fields/html_mail_field/html_mail_field";
import { after, before, beforeEach, expect, test } from "@odoo/hoot";
import { press, queryOne } from "@odoo/hoot-dom";
import { animationFrame, enableTransitions } from "@odoo/hoot-mock";
import {
    clickSave,
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
            `<h1 style="border-radius:0px;border-style:none;padding:0px;margin:0px 0 8px 0;box-sizing:border-box;border-left-color:#111827;border-bottom-color:#111827;border-right-color:#111827;border-top-color:#111827;border-left-width:0px;border-bottom-width:0px;border-right-width:0px;border-top-width:0px;font-size: []px;color:#111827;line-height:1.2;font-weight:500;font-family:'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Ubuntu, 'Noto Sans', Arial, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji';">first</h1>`
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

    await clickSave();
    await expect.waitForSteps(["web_save"]);
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

// TODO: re-enable and adapt this test when the frontend method `fontToImg` and
// the controller /mail/font_to_img/ is fixed to handle material symbols icons
test.skip("HtmlMail add icon and save inline html", async function () {
    enableTransitions();
    useCustomStyleRules(
        `.test-icon-inline .note-editable .fa {
            color: rgb(55,65,81) !important;
            background-color: rgb(249,250,251) !important;
        }
        p, img {
            border-color: #ff0000 !important;
        }
        `
    );
    onRpc("web_save", ({ args }) => {
        expect(args[1].body).toBe(
            `<p style="border-radius:0px;border-style:none;padding:0px;margin:0px 0 16px 0;box-sizing:border-box;border-left-width:0px;border-bottom-width:0px;border-right-width:0px;border-top-width:0px;border-left-color:#ff0000;border-bottom-color:#ff0000;border-right-color:#ff0000;border-top-color:#ff0000;"><span style="border-radius: 0px; border-style: none; padding: 0px; margin: 0px; box-sizing: border-box; border-color: #111827; border-width: 0px; font-weight: 400; font-feature-settings: 'liga'; direction: ltr; overflow-wrap: normal; white-space: nowrap; text-transform: none; letter-spacing: normal; line-height: 1; font-variation-settings: 'FILL' 0, 'opsz' 24; font-size: 14px; font-style: normal; font-family: material_symbols_outlined; display: inline-block; width: 14.0156px; height: 15px; vertical-align: text-bottom;" class="oe_unbreakable  oi" width="14.0156"><img width="14.0156" height="17" src="/mail/font_to_img/108/rgb(55%2C65%2C81)/rgb(249%2C250%2C251)/14x17" data-class="fa fa-glass oi" data-style="null" style="border-radius:0px;border-style:none;padding:0px;margin:0px;border-left-width:0px;border-bottom-width:0px;border-right-width:0px;border-top-width:0px;border-left-color:#ff0000;border-bottom-color:#ff0000;border-right-color:#ff0000;border-top-color:#ff0000;box-sizing: border-box; line-height: 14px; width: 14.0156px; height: 17px; vertical-align: unset;"></span>first</p>`
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

    await contains("button.nav-link:contains('Icons')").click();
    await contains("span.fa-glass").click();

    await clickSave();
    await expect.waitForSteps(["web_save"]);
});
