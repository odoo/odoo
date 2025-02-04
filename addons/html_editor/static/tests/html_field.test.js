import { HtmlField } from "@html_editor/fields/html_field";
import { MediaDialog } from "@html_editor/main/media/media_dialog/media_dialog";
import { stripHistoryIds } from "@html_editor/others/collaboration/collaboration_odoo_plugin";
import {
    getEditableDescendants,
    getEmbeddedProps,
} from "@html_editor/others/embedded_component_utils";
import { READONLY_MAIN_EMBEDDINGS } from "@html_editor/others/embedded_components/embedding_sets";
import { normalizeHTML, parseHTML } from "@html_editor/utils/html";
import { Wysiwyg } from "@html_editor/wysiwyg";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import {
    click,
    press,
    queryAll,
    queryAllTexts,
    queryOne,
    waitFor,
    waitUntil,
} from "@odoo/hoot-dom";
import { Deferred, animationFrame, mockSendBeacon, tick } from "@odoo/hoot-mock";
import { onWillDestroy, xml } from "@odoo/owl";
import {
    clickSave,
    contains,
    defineModels,
    defineParams,
    fields,
    models,
    mountView,
    mountViewInDialog,
    onRpc,
    patchWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";
import { assets } from "@web/core/assets";
import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { Counter, EmbeddedWrapperMixin } from "./_helpers/embedded_component";
import { moveSelectionOutsideEditor, setSelection } from "./_helpers/selection";
import { insertText, pasteOdooEditorHtml, pasteText, undo } from "./_helpers/user_actions";

class Partner extends models.Model {
    txt = fields.Html({ trim: true });
    name = fields.Char();

    _records = [
        { id: 1, name: "first", txt: "<p>first</p>" },
        { id: 2, name: "second", txt: "<p>second</p>" },
    ];

    _onChanges = {
        name(record) {
            if (record.name) {
                record.txt = `<p>${record.name}</p>`;
            }
        },
    };
}

class IrAttachment extends models.Model {
    _name = "ir.attachment";
    name = fields.Char();
    description = fields.Char();
    mimetype = fields.Char();
    checksum = fields.Char();
    url = fields.Char();
    type = fields.Char();
    res_id = fields.Integer();
    res_model = fields.Char();
    public = fields.Boolean();
    access_token = fields.Char();
    image_src = fields.Char();
    image_width = fields.Integer();
    image_height = fields.Integer();
    original_id = fields.Many2one({ relation: "ir.attachment" });

    _records = [
        {
            id: 1,
            name: "image",
            description: "",
            mimetype: "image/png",
            checksum: false,
            url: "/web/image/123/transparent.png",
            type: "url",
            res_id: 0,
            res_model: false,
            public: true,
            access_token: false,
            image_src: "/web/image/123/transparent.png",
            image_width: 256,
            image_height: 256,
        },
    ];
}
defineModels([Partner, IrAttachment]);

let htmlEditor;
beforeEach(() => {
    patchWithCleanup(HtmlField.prototype, {
        onEditorLoad(editor) {
            htmlEditor = editor;
            return super.onEditorLoad(...arguments);
        },
    });
});

function setSelectionInHtmlField(selector = "p", fieldName = "txt") {
    const anchorNode = queryOne(`[name='${fieldName}'] .odoo-editor-editable ${selector}`);
    setSelection({ anchorNode, anchorOffset: 0 });
    return anchorNode;
}

test("html field in readonly", async () => {
    await mountView({
        type: "form",
        resId: 1,
        resIds: [1, 2],
        resModel: "partner",
        arch: `
            <form>
                <field name="txt" widget="html" readonly="1"/>
            </form>`,
    });
    expect(".odoo-editor-editable").toHaveCount(0);
    expect(`[name="txt"] .o_readonly`).toHaveCount(1);
    expect(`[name="txt"] .o_readonly`).toHaveInnerHTML("<p>first</p>");

    await contains(`.o_pager_next`).click();
    expect(".odoo-editor-editable").toHaveCount(0);
    expect(`[name="txt"] .o_readonly`).toHaveCount(1);
    expect(`[name="txt"] .o_readonly`).toHaveInnerHTML("<p>second</p>");

    await contains(`.o_pager_previous`).click();
    expect(".odoo-editor-editable").toHaveCount(0);
    expect(`[name="txt"] .o_readonly`).toHaveCount(1);
    expect(`[name="txt"] .o_readonly`).toHaveInnerHTML("<p>first</p>");
});

test("html field in readonly updated by onchange", async () => {
    await mountView({
        type: "form",
        resId: 1,
        resIds: [1, 2],
        resModel: "partner",
        arch: `
            <form>
                <field name="name"/>
                <field name="txt" widget="html" readonly="1"/>
            </form>`,
    });
    expect(".odoo-editor-editable").toHaveCount(0);
    expect(`[name="txt"] .o_readonly`).toHaveCount(1);
    expect(`[name="txt"] .o_readonly`).toHaveInnerHTML("<p>first</p>");

    await contains(`.o_field_widget[name=name] input`).edit("hello");
    expect(".odoo-editor-editable").toHaveCount(0);
    expect(`[name="txt"] .o_readonly`).toHaveCount(1);
    expect(`[name="txt"] .o_readonly`).toHaveInnerHTML("<p>hello</p>");
});

test("html field in readonly with embedded components", async () => {
    patchWithCleanup(Counter, {
        template: xml`
            <span t-ref="root" class="counter" t-on-click="increment"><t t-esc="props.name || ''"/>:<t t-esc="state.value"/></span>`,
    });
    const unpatch = patch(Counter.prototype, {
        setup() {
            super.setup();
            onWillDestroy(() => {
                this.testOnWillDestroy?.();
            });
        },
        testOnWillDestroy() {
            expect.step("destroyed");
        },
    });
    // patchWithCleanup Array => cleanup keeps the last array entry set to undefined,
    // so it can not be used
    READONLY_MAIN_EMBEDDINGS.push({
        name: "counter",
        Component: Counter,
        getProps: (host) => ({
            ...getEmbeddedProps(host),
        }),
    });
    Partner._records = [
        {
            id: 1,
            txt: `<div><span data-embedded="counter" data-embedded-props='{"name":"name"}'></span></div>`,
        },
    ];
    Partner._onChanges = {
        name(record) {
            record.txt = `<div><span data-embedded="counter"></span></div>`;
        },
    };
    await mountView({
        type: "form",
        resId: 1,
        resIds: [1],
        resModel: "partner",
        arch: `
            <form>
                <field name="name"/>
                <field name="txt" widget="html" readonly="1" options="{'embedded_components': True}"/>
            </form>`,
    });
    expect(".odoo-editor-editable").toHaveCount(0);
    expect(`[name="txt"] .o_readonly`).toHaveCount(1);
    expect(`[name="txt"] .o_readonly`).toHaveInnerHTML(
        `<div><span data-embedded="counter" data-embedded-props='{"name":"name"}'><span class="counter">name:0</span></div>`
    );
    click(".counter");
    await animationFrame();
    expect(`[name="txt"] .o_readonly`).toHaveInnerHTML(
        `<div><span data-embedded="counter" data-embedded-props='{"name":"name"}'><span class="counter">name:1</span></div>`
    );
    // trigger the onchange method for name, which will replace the txt value.
    await contains(`.o_field_widget[name=name] input`).edit("hello");
    await animationFrame();
    expect.verifySteps(["destroyed"]);
    expect(`[name="txt"] .o_readonly`).toHaveInnerHTML(
        `<div><span data-embedded="counter"><span class="counter">:0</span></div>`
    );
    unpatch();
    READONLY_MAIN_EMBEDDINGS.pop();
});

test("html field in readonly with embedded components and editable descendants", async () => {
    const Wrapper = EmbeddedWrapperMixin("editable");
    // patchWithCleanup Array => cleanup keeps the last array entry set to undefined,
    // so it can not be used
    READONLY_MAIN_EMBEDDINGS.push(
        {
            name: "wrapper",
            Component: Wrapper,
            getProps: (host) => ({ host }),
            getEditableDescendants,
        },
        {
            name: "counter",
            Component: Counter,
        }
    );
    Partner._records = [
        {
            id: 1,
            txt: `<div data-embedded="wrapper"><div data-embedded-editable="editable"><span data-embedded="counter"></span></div></div>`,
        },
    ];
    await mountView({
        type: "form",
        resId: 1,
        resIds: [1],
        resModel: "partner",
        arch: `
            <form>
                <field name="name"/>
                <field name="txt" widget="html" readonly="1" options="{'embedded_components': True}"/>
            </form>`,
    });
    expect(".odoo-editor-editable").toHaveCount(0);
    expect(`[name="txt"] .o_readonly`).toHaveCount(1);
    expect(`[name="txt"] .o_readonly`).toHaveInnerHTML(
        `<div data-embedded="wrapper"><div class="editable"><div data-embedded-editable="editable"><span data-embedded="counter"><span class="counter">Counter:0</span></span></div></div></div>`
    );
    click(".counter");
    await animationFrame();
    expect(`[name="txt"] .o_readonly`).toHaveInnerHTML(
        `<div data-embedded="wrapper"><div class="editable"><div data-embedded-editable="editable"><span data-embedded="counter"><span class="counter">Counter:1</span></span></div></div></div>`
    );
    READONLY_MAIN_EMBEDDINGS.pop();
    READONLY_MAIN_EMBEDDINGS.pop();
});

test("links should open on a new tab in readonly", async () => {
    Partner._records = [
        {
            id: 1,
            txt: `
            <body>
                <p>first</p>
                <a href="/contactus">Relative link</a>
                <a href="${browser.location.origin}/contactus">Internal link</a>
                <a href="https://google.com">External link</a>
            </body>`,
        },
        {
            id: 2,
            txt: `
            <body>
                <p>second</p>
                <a href="/contactus2">Relative link</a>
                <a href="${browser.location.origin}/contactus2">Internal link</a>
                <a href="https://google2.com">External link</a>
            </body>`,
        },
    ];
    await mountView({
        type: "form",
        resId: 1,
        resIds: [1, 2],
        resModel: "partner",
        arch: `
            <form>
                <field name="txt" widget="html" readonly="1"/>
            </form>`,
    });

    expect("[name='txt'] p").toHaveText("first");
    for (const link of queryAll("a")) {
        expect(link.getAttribute("target")).toBe("_blank");
        expect(link.getAttribute("rel")).toBe("noreferrer");
    }

    await contains(`.o_pager_next`).click();
    expect("[name='txt'] p").toHaveText("second");
    for (const link of queryAll("a")) {
        expect(link.getAttribute("target")).toBe("_blank");
        expect(link.getAttribute("rel")).toBe("noreferrer");
    }
});

test("XML-like self-closing elements are fixed in readonly mode", async () => {
    Partner._records = [
        {
            id: 1,
            txt: `<a href="#"/>outside<a href="#">inside</a>`,
        },
    ];
    await mountView({
        type: "form",
        resId: 1,
        resIds: [1, 2],
        resModel: "partner",
        arch: `
            <form>
                <field name="txt" widget="html" readonly="1"/>
            </form>`,
    });
    expect(".odoo-editor-editable").toHaveCount(0);
    expect(`[name="txt"] .o_readonly`).toHaveCount(1);
    expect(`[name="txt"] .o_readonly`).toHaveInnerHTML(
        `<a href="#" target="_blank" rel="noreferrer"></a>outside<a href="#" target="_blank" rel="noreferrer">inside</a>`
    );
});

test("XML-like self-closing elements are fixed in editable mode", async () => {
    Partner._records = [
        {
            id: 1,
            txt: `<a href="#"/>outside<a href="#">inside</a>`,
        },
    ];
    await mountView({
        type: "form",
        resId: 1,
        resIds: [1, 2],
        resModel: "partner",
        arch: `
            <form>
                <field name="txt" widget="html"/>
            </form>`,
    });
    expect(".odoo-editor-editable").toHaveCount(1);
    expect(`[name="txt"] .o_readonly`).toHaveCount(0);
    expect(`[name="txt"] .odoo-editor-editable`).toHaveInnerHTML(
        `<div class="o-paragraph">outside<a href="#">inside</a></div>`
    );
});

test("edit and save a html field", async () => {
    onRpc("web_save", ({ args }) => {
        expect(args[1]).toEqual({
            txt: "<p>testfirst</p>",
        });
        expect.step("web_save");
    });

    await mountView({
        type: "form",
        resId: 1,
        resIds: [1, 2],
        resModel: "partner",
        arch: `
            <form>
                <field name="txt" widget="html"/>
            </form>`,
    });
    expect(".odoo-editor-editable p").toHaveText("first");
    expect(`.o_form_button_save`).not.toBeVisible();

    setSelectionInHtmlField();
    await insertText(htmlEditor, "test");
    await animationFrame();
    expect(".odoo-editor-editable p").toHaveText("testfirst");
    expect(".o_form_button_save").toBeVisible();

    await contains(".o_form_button_save").click();
    expect.verifySteps(["web_save"]);
    expect(".odoo-editor-editable p").toHaveText("testfirst");
    expect(`.o_form_button_save`).not.toBeVisible();
});

test("edit and save a html field containing JSON as some attribute values should keep the same wysiwyg", async () => {
    patchWithCleanup(Wysiwyg.prototype, {
        setup() {
            super.setup();
            expect.step("Setup Wysiwyg");
        },
    });
    onRpc("partner", "web_save", ({ args }) => {
        expect.step("web_save");
        // server representation does not have HTML entities
        args[1].txt = `<div data-value='{"myString":"myString"}'><p>content</p></div><p>first</p>`;
    });

    await mountView({
        type: "form",
        resId: 1,
        resModel: "partner",
        arch: `
            <form>
                <field name="txt" widget="html"/>
            </form>`,
    });
    setSelectionInHtmlField();
    const value = JSON.stringify({
        myString: "myString",
    });
    pasteOdooEditorHtml(htmlEditor, `<div data-value=${value}><p>content</p></div>`);
    const txtField = queryOne('.o_field_html[name="txt"] .odoo-editor-editable');
    expect(txtField).toHaveInnerHTML(
        `<div data-value="{&quot;myString&quot;:&quot;myString&quot;}"><p>content</p></div><p>first</p>`
    );
    expect.verifySteps(["Setup Wysiwyg"]);

    await clickSave();
    expect.verifySteps(["web_save"]);
});

test("edit a html field in new form view dialog and close the dialog with 'escape'", async () => {
    await mountViewInDialog({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="name"></field>
                <field name="txt" widget="html"/>
            </form>`,
    });
    expect(".modal").toHaveCount(1);
    expect(".odoo-editor-editable div.o-paragraph").toHaveText("");

    await contains("[name='txt'] .odoo-editor-editable").focus();
    setSelectionInHtmlField("div.o-paragraph");
    await insertText(htmlEditor, "test");
    await animationFrame();
    expect(".odoo-editor-editable div.o-paragraph").toHaveText("test");
    expect(".o_form_button_save").toBeVisible();

    await press("escape");
    await animationFrame();
    expect(".modal").toHaveCount(0);
});

test("onchange update html field in edition", async () => {
    onRpc("web_save", ({ args }) => {
        expect(args[1]).toEqual({
            txt: "<p>testfirst</p>",
        });
        expect.step("web_save");
    });

    await mountView({
        type: "form",
        resId: 1,
        resIds: [1, 2],
        resModel: "partner",
        arch: `
            <form>
                <field name="name"/>
                <field name="txt" widget="html"/>
            </form>`,
    });
    expect(".odoo-editor-editable p").toHaveText("first");

    await contains(`.o_field_widget[name=name] input`).edit("hello");
    await animationFrame();
    expect(".odoo-editor-editable p").toHaveText("hello");
});

test("create new record and load it correctly", async () => {
    class Composer extends models.Model {
        linked_composer_id = fields.Many2one({ relation: "composer" });
        name = fields.Char();
        body = fields.Html({ trim: true });

        _records = [
            {
                id: 1,
                linked_composer_id: 2,
                name: "first",
                body: "<p>2</p>",
            },
            {
                id: 2,
                name: "second",
                linked_composer_id: 1,
                body: "<p></p>",
            },
        ];

        // Necessary for mobile
        _views = {
            "kanban,false": `
                <kanban>
                    <templates>
                        <t t-name="card">
                            <field name="name"/>
                        </t>
                    </templates>
                </kanban>
            `,
        };

        _onChanges = {
            linked_composer_id(record) {
                record.body = `<p>${record.linked_composer_id}</p>`;
            },
        };
    }
    defineModels([Composer]);
    await mountView({
        type: "form",
        resId: 1,
        resModel: "composer",
        arch: `
            <form>
                <field name="body" widget="html"/>
                <field name="linked_composer_id"/>
            </form>`,
    });

    expect(".odoo-editor-editable").toHaveCount(1);
    expect(".odoo-editor-editable").toHaveInnerHTML("<p>2</p>");
    await contains(".o_input#linked_composer_id_0").click();
    await animationFrame();
    await contains(".ui-menu-item:contains(first), .o_kanban_record:contains(first)").click();
    await animationFrame();
    expect(".odoo-editor-editable").toHaveInnerHTML("<p>1</p>");
    await contains(".o_input#linked_composer_id_0").click();
    await animationFrame();
    await contains(".ui-menu-item:contains(second), .o_kanban_record:contains(second)").click();
    await animationFrame();
    expect(".odoo-editor-editable").toHaveInnerHTML("<p>2</p>");
});

test.tags("focus required");
test("edit html field and blur multiple time should apply 1 onchange", async () => {
    const def = new Deferred();
    Partner._onChanges = {
        txt() {},
    };
    onRpc("partner", "onchange", async ({ args }) => {
        expect.step(`onchange: ${args[1].txt}`);
        await def;
    });
    await mountView({
        type: "form",
        resId: 1,
        resIds: [1, 2],
        resModel: "partner",
        arch: `
            <form>
                <field name="name"/>
                <field name="txt" widget="html" options="{'codeview': true}"/>
            </form>`,
    });

    setSelectionInHtmlField();
    await insertText(htmlEditor, "Hello ");
    expect("[name='txt'] .odoo-editor-editable").toHaveInnerHTML("<p>Hello first </p>");

    await contains("[name='name'] input").click();
    expect.verifySteps(["onchange: <p>Hello first</p>"]);

    await contains("[name='txt'] .odoo-editor-editable").focus();
    await contains("[name='name'] input").click();
    def.resolve();
    await animationFrame();
    expect.verifySteps([]);
});

test.tags("focus required");
test("edit an html field during an onchange", async () => {
    const def = new Deferred();
    Partner._onChanges = {
        txt(record) {
            record.txt = "<p>New Value</p>";
        },
    };
    onRpc("partner", "onchange", async ({ args }) => {
        expect.step(`onchange: ${args[1].txt}`);
        await def;
    });
    await mountView({
        type: "form",
        resId: 1,
        resIds: [1, 2],
        resModel: "partner",
        arch: `
            <form>
                <field name="txt" widget="html" options="{'codeview': true}"/>
            </form>`,
    });

    setSelectionInHtmlField();
    await insertText(htmlEditor, "Hello ");
    expect("[name='txt'] .odoo-editor-editable").toHaveInnerHTML("<p>Hello first </p>");

    await contains(".o_form_view").click();
    expect.verifySteps(["onchange: <p>Hello first</p>"]);

    setSelectionInHtmlField();
    await insertText(htmlEditor, "Yop ");
    expect("[name='txt'] .odoo-editor-editable").toHaveInnerHTML("<p>Yop Hello first </p>");

    def.resolve();
    await animationFrame();
    expect("[name='txt'] .odoo-editor-editable").toHaveInnerHTML("<p>Yop Hello first </p>");
});

test("click on next/previous page", async () => {
    await mountView({
        type: "form",
        resId: 1,
        resIds: [1, 2],
        resModel: "partner",
        arch: `
            <form>
                <field name="txt" widget="html"/>
            </form>`,
    });
    expect(".odoo-editor-editable p:contains(first)").toHaveCount(1);

    await contains(`.o_pager_next`).click();
    expect(".odoo-editor-editable p:contains(second)").toHaveCount(1);

    await contains(`.o_pager_previous`).click();
    expect(".odoo-editor-editable p:contains(first)").toHaveCount(1);
});

test("edit and switch page", async () => {
    onRpc("web_save", ({ args }) => {
        expect(args[1]).toEqual({
            txt: "<p>testfirst</p>",
        });
        expect.step("web_save");
    });
    await mountView({
        type: "form",
        resId: 1,
        resIds: [1, 2],
        resModel: "partner",
        arch: `
            <form>
                <field name="txt" widget="html"/>
            </form>`,
    });
    expect(".odoo-editor-editable p").toHaveText("first");
    expect(`.o_form_button_save`).not.toBeVisible();

    setSelectionInHtmlField();
    await insertText(htmlEditor, "test");
    await animationFrame();
    expect(".odoo-editor-editable p").toHaveText("testfirst");
    expect(`.o_form_button_save`).toBeVisible();

    await contains(`.o_pager_next`).click();
    await animationFrame();
    expect(".odoo-editor-editable p").toHaveText("second");
    expect(`.o_form_button_save`).not.toBeVisible();
    expect.verifySteps(["web_save"]);

    await contains(`.o_pager_previous`).click();
    expect(".odoo-editor-editable p").toHaveText("testfirst");
    expect(`.o_form_button_save`).not.toBeVisible();
});

test("discard changes in html field in form", async () => {
    await mountView({
        type: "form",
        resId: 1,
        resIds: [1, 2],
        resModel: "partner",
        arch: `
            <form>
                <field name="txt" widget="html"/>
            </form>`,
    });
    expect(".odoo-editor-editable p").toHaveText("first");
    expect(`.o_form_button_save`).not.toBeVisible();

    // move the hoot focus in the editor
    await click(".odoo-editor-editable");
    setSelectionInHtmlField();
    await insertText(htmlEditor, "test");
    await animationFrame();
    expect(".odoo-editor-editable p").toHaveText("testfirst");
    expect(`.o_form_button_cancel`).toBeVisible();

    await contains(`.o_form_button_cancel`).click();
    await animationFrame();
    expect(".odoo-editor-editable p").toHaveText("first");
    expect(`.o_form_button_cancel`).not.toBeVisible();
});

test("undo after discard html field changes in form", async () => {
    await mountView({
        type: "form",
        resId: 1,
        resIds: [1, 2],
        resModel: "partner",
        arch: `
            <form>
                <field name="txt" widget="html"/>
            </form>`,
    });
    expect(".odoo-editor-editable p").toHaveText("first");
    expect(`.o_form_button_save`).not.toBeVisible();

    // move the hoot focus in the editor
    await click(".odoo-editor-editable");
    setSelectionInHtmlField();
    await insertText(htmlEditor, "test");
    await animationFrame();
    expect(".odoo-editor-editable p").toHaveText("testfirst");
    expect(`.o_form_button_cancel`).toBeVisible();

    await press(["ctrl", "z"]);
    expect(".odoo-editor-editable p").toHaveText("tesfirst");
    expect(`.o_form_button_cancel`).toBeVisible();

    await contains(`.o_form_button_cancel`).click();
    await animationFrame();
    expect(".odoo-editor-editable p").toHaveText("first");
    expect(`.o_form_button_cancel`).not.toBeVisible();

    await press(["ctrl", "z"]);
    expect(".odoo-editor-editable p").toHaveText("first");
    expect(`.o_form_button_cancel`).not.toBeVisible();
});

test("A new MediaDialog after switching record in a Form view should have the correct resId", async () => {
    patchWithCleanup(MediaDialog.prototype, {
        setup() {
            expect.step(`${this.props.resModel} : ${this.props.resId}`);
            this.size = "xl";
            this.contentClass = "o_select_media_dialog";
            this.title = "TEST";
            this.tabs = [];
            this.state = {};
            // no call to super to avoid services dependencies
            // this test only cares about the props given to the dialog
        },
    });
    await mountView({
        type: "form",
        resId: 1,
        resIds: [1, 2],
        resModel: "partner",
        arch: `
                <form>
                    <field name="txt" widget="html"/>
                </form>`,
    });
    expect(".odoo-editor-editable p:contains(first)").toHaveCount(1);

    await contains(`.o_pager_next`).click();
    expect(".odoo-editor-editable p:contains(second)").toHaveCount(1);

    setSelectionInHtmlField();
    await insertText(htmlEditor, "/Media");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);
    expect(".active .o-we-command-name").toHaveText("Media");

    await press("Enter");
    await animationFrame();
    expect.verifySteps(["partner : 2"]);
});

test("Embed video by pasting video URL", async () => {
    Partner._records = [
        {
            id: 1,
            txt: "<p><br></p>",
        },
    ];

    onRpc("/html_editor/video_url/data", async () => {
        return {
            platform: "youtube",
            embed_url: "//www.youtube.com/embed/qxb74CMR748?rel=0&autoplay=0",
        };
    });

    await mountView({
        type: "form",
        resId: 1,
        resModel: "partner",
        arch: `
            <form>
                <field name="txt" widget="html"/>
            </form>`,
    });

    const anchorNode = setSelectionInHtmlField();

    // Paste a video URL.
    pasteText(htmlEditor, "https://www.youtube.com/watch?v=qxb74CMR748");
    await animationFrame();
    expect(anchorNode.outerHTML).toBe("<p>https://www.youtube.com/watch?v=qxb74CMR748</p>");
    expect(".o-we-powerbox").toHaveCount(1);
    expect(queryAllTexts(".o-we-command-name")).toEqual(["Embed Youtube Video", "Paste as URL"]);

    // Press Enter to select first option in the powerbox ("Embed Youtube Video").
    await press("Enter");
    await animationFrame();
    expect(anchorNode.outerHTML).toBe("<p></p>");
    expect(
        'div.media_iframe_video iframe[src="//www.youtube.com/embed/qxb74CMR748?rel=0&autoplay=0"]'
    ).toHaveCount(1);
});

test("isDirty should be false when the content is being transformed by the editor", async () => {
    Partner._records = [
        {
            id: 1,
            txt: "<p><b>ab</b><b>c</b></p>",
        },
    ];
    await mountView({
        type: "form",
        resId: 1,
        resModel: "partner",
        arch: `
            <form>
                <field name="txt" widget="html"/>
            </form>`,
    });

    expect(`[name='txt'] .odoo-editor-editable`).toHaveInnerHTML("<p><b>abc</b></p>", {
        message: "value should be sanitized by the editor",
    });
    expect(`.o_form_button_save`).not.toBeVisible();
});

test.tags("desktop");
test("link preview in Link Popover", async () => {
    Partner._records = [
        {
            id: 1,
            txt: "<p class='test_target'>abc<a href='/test'>This website</a></p>",
        },
    ];
    await mountView({
        type: "form",
        resId: 1,
        resModel: "partner",
        arch: `
            <form>
                <field name="txt" widget="html"/>
            </form>`,
    });

    expect(".test_target a").toHaveText("This website");

    // Open the popover option to edit the link
    setSelectionInHtmlField(".test_target a");
    await animationFrame();
    // Click on the edit link icon
    await contains("a.o_we_edit_link").click();
    expect(".o-we-linkpopover input.o_we_label_link").toHaveValue("This website", {
        message: "The label input field should match the link's content",
    });
    expect(".o-we-linkpopover a#link-preview").toHaveText("This website", {
        message: "Link label in preview should match label input field",
    });

    await contains(".o-we-linkpopover input.o_we_label_link").edit("Bad new label");
    expect(".o-we-linkpopover input.o_we_label_link").toHaveValue("Bad new label", {
        message: "The label input field should match the link's content",
    });
    expect(".o-we-linkpopover a#link-preview").toHaveText("Bad new label", {
        message: "Link label in preview should match label input field",
    });
    // Move selection outside to discard
    setSelectionInHtmlField(".test_target");
    await waitUntil(() => !document.querySelector(".o-we-linkpopover"), { timeout: 500 });
    expect(".o-we-linkpopover").toHaveCount(0);
    expect(".test_target a").toHaveText("This website");

    // Select link label to open the floating toolbar.
    setSelectionInHtmlField(".test_target a");
    await animationFrame();
    // Click on the edit link icon
    await contains("a.o_we_edit_link").click();
    expect(".o-we-linkpopover input.o_we_label_link").toHaveValue("This website", {
        message: "The label input field should match the link's content",
    });
    expect(".o-we-linkpopover a#link-preview").toHaveText("This website", {
        message: "Link label in preview should match label input field",
    });

    // Open the popover option to edit the link
    await contains(".o-we-linkpopover input.o_we_label_link").edit("New label");
    expect(".o-we-linkpopover a#link-preview").toHaveText("New label", {
        message: "Preview should be updated on label input field change",
    });

    // Click "Save".
    await contains(".o-we-linkpopover .o_we_apply_link").click();
    expect(".test_target a").toHaveText("New label", {
        message: "The link's label should be updated",
    });
});

test("html field with a placeholder", async () => {
    Partner._records = [
        {
            id: 1,
            txt: false,
        },
    ];
    await mountView({
        type: "form",
        resId: 1,
        resModel: "partner",
        arch: `
            <form>
                <field name="txt" widget="html" placeholder="test"/>
            </form>`,
    });

    expect(`[name="txt"] .odoo-editor-editable`).toHaveInnerHTML(
        '<div class="o-paragraph o-we-hint" placeholder="test"><br></div>',
        { type: "html" }
    );

    setSelectionInHtmlField("div.o-paragraph");
    await tick();
    expect(`[name="txt"] .odoo-editor-editable`).toHaveInnerHTML(
        '<div class="o-paragraph o-we-hint" placeholder="Type &quot;/&quot; for commands"><br></div>',
        { type: "html" }
    );

    moveSelectionOutsideEditor();
    await tick();
    expect(`[name="txt"] .odoo-editor-editable`).toHaveInnerHTML(
        '<div class="o-paragraph o-we-hint" placeholder="test"><br></div>',
        { type: "html" }
    );
});

test("'Video Link' command is available", async () => {
    await mountView({
        type: "form",
        resId: 1,
        resModel: "partner",
        arch: `
            <form>
                <field name="txt" widget="html"/>
            </form>`,
    });
    setSelectionInHtmlField();
    await insertText(htmlEditor, "/video");
    await waitFor(".o-we-powerbox");
    expect(queryAllTexts(".o-we-command-name")).toEqual(["Video Link"]);
});

test("MediaDialog contains 'Videos' tab by default in html field", async () => {
    await mountView({
        type: "form",
        resId: 1,
        resModel: "partner",
        arch: `
            <form>
                <field name="txt" widget="html"/>
            </form>`,
    });
    setSelectionInHtmlField();
    await insertText(htmlEditor, "/media");
    await waitFor(".o-we-powerbox");
    expect(queryAllTexts(".o-we-command-name")[0]).toBe("Media");

    await press("Enter");
    await animationFrame();
    expect(queryAllTexts(".o_select_media_dialog .nav-tabs .nav-item")).toEqual([
        "Images",
        "Documents",
        "Icons",
        "Videos",
    ]);
});

test("MediaDialog does not contain 'Videos' tab in html field when 'disableVideo' = true", async () => {
    await mountView({
        type: "form",
        resId: 1,
        resModel: "partner",
        arch: `
            <form>
            <field name="txt" widget="html" options="{'disableVideo': True}"/>
            </form>`,
    });

    setSelectionInHtmlField();
    await insertText(htmlEditor, "/media");
    await waitFor(".o-we-powerbox");
    expect(queryAllTexts(".o-we-command-name")[0]).toBe("Media");

    await press("Enter");
    await animationFrame();
    expect(queryAllTexts(".o_select_media_dialog .nav-tabs .nav-item")).toEqual([
        "Images",
        "Documents",
        "Icons",
    ]);
});

test("MediaDialog does not contain 'Videos' tab when sanitize = true", async () => {
    class SanitizePartner extends models.Model {
        _name = "sanitize.partner";

        txt = fields.Html({ sanitize: true });
        _records = [{ id: 1, txt: "<p>first sanitize</p>" }];
    }

    defineModels([SanitizePartner]);
    await mountView({
        type: "form",
        resId: 1,
        resModel: "sanitize.partner",
        arch: `
            <form>
                <field name="txt" widget="html"/>
            </form>`,
    });
    setSelectionInHtmlField();
    await insertText(htmlEditor, "/media");
    await waitFor(".o-we-powerbox");
    expect(queryAllTexts(".o-we-command-name")[0]).toBe("Media");

    await press("Enter");
    await animationFrame();
    expect(queryAllTexts(".o_select_media_dialog .nav-tabs .nav-item")).toEqual([
        "Images",
        "Documents",
        "Icons",
    ]);
});

test("MediaDialog contains 'Videos' tab when sanitize_tags = true and 'disableVideo' = false", async () => {
    class SanitizePartner extends models.Model {
        _name = "sanitize.partner";

        txt = fields.Html({ sanitize_tags: true });
        _records = [{ id: 1, txt: "<p>first sanitize tags</p>" }];
    }

    defineModels([SanitizePartner]);
    await mountView({
        type: "form",
        resId: 1,
        resModel: "sanitize.partner",
        arch: `
            <form>
                <field name="txt" widget="html" options="{'disableVideo': False}"/>
            </form>`,
    });
    setSelectionInHtmlField();
    await insertText(htmlEditor, "/media");
    await waitFor(".o-we-powerbox");
    expect(queryAllTexts(".o-we-command-name")[0]).toBe("Media");

    await press("Enter");
    await animationFrame();
    expect(queryAllTexts(".o_select_media_dialog .nav-tabs .nav-item")).toEqual([
        "Images",
        "Documents",
        "Icons",
        "Videos",
    ]);
});

test("'Media' command is available by default", async () => {
    await mountView({
        type: "form",
        resId: 1,
        resModel: "partner",
        arch: `
            <form>
                <field name="txt" widget="html"/>
            </form>`,
    });
    setSelectionInHtmlField();
    await insertText(htmlEditor, "/media");
    await waitFor(".o-we-powerbox");
    expect(queryAllTexts(".o-we-command-name")[0]).toBe("Media");
});

test("'Media' command is not available when 'disableImage' = true", async () => {
    await mountView({
        type: "form",
        resId: 1,
        resModel: "partner",
        arch: `
            <form>
                <field name="txt" widget="html" options="{'disableImage': True}"/>
            </form>`,
    });
    setSelectionInHtmlField();
    await insertText(htmlEditor, "/media");
    await animationFrame();
    expect(queryAllTexts(".o-we-command-name")).not.toInclude("Media");
});

test("codeview is not available by default", async () => {
    await mountView({
        type: "form",
        resId: 1,
        resModel: "partner",
        arch: `
            <form>
                <field name="txt" widget="html"/>
            </form>`,
    });
    const node = queryOne(".odoo-editor-editable p");
    setSelection({ anchorNode: node, anchorOffset: 0, focusNode: node, focusOffset: 1 });
    await waitFor(".o-we-toolbar");
    expect(".o-we-toolbar button[name='codeview']").toHaveCount(0);
});

test("codeview is not available when not in debug mode", async () => {
    patchWithCleanup(odoo, { debug: false });
    await mountView({
        type: "form",
        resId: 1,
        resModel: "partner",
        arch: `
            <form>
                <field name="txt" widget="html" options="{'codeview': true}"/>
            </form>`,
    });
    const node = queryOne(".odoo-editor-editable p");
    setSelection({ anchorNode: node, anchorOffset: 0, focusNode: node, focusOffset: 1 });
    await waitFor(".o-we-toolbar");
    expect(".o-we-toolbar button[name='codeview']").toHaveCount(0);
});

test("codeview is available when option is active and in debug mode", async () => {
    patchWithCleanup(odoo, { debug: true });
    await mountView({
        type: "form",
        resId: 1,
        resModel: "partner",
        arch: `
            <form>
                <field name="txt" widget="html" options="{'codeview': true}"/>
            </form>`,
    });
    const node = queryOne(".odoo-editor-editable p");
    setSelection({ anchorNode: node, anchorOffset: 0, focusNode: node, focusOffset: 1 });
    await waitFor(".o-we-toolbar");
    expect(".o-we-toolbar button[name='codeview']").toHaveCount(1);
});

test("enable/disable codeview with editor toolbar", async () => {
    patchWithCleanup(odoo, { debug: true });
    await mountView({
        type: "form",
        resId: 1,
        resIds: [1, 2],
        resModel: "partner",
        arch: `
            <form>
                <field name="txt" widget="html" options="{'codeview': true}"/>
            </form>`,
    });
    expect("[name='txt'] .odoo-editor-editable").toHaveInnerHTML("<p> first </p>");
    expect("[name='txt'] textarea").toHaveCount(0);

    // Switch to code view
    const node = queryOne(".odoo-editor-editable p");
    setSelection({ anchorNode: node, anchorOffset: 0, focusNode: node, focusOffset: 1 });
    await waitFor(".o-we-toolbar");
    await contains(".o-we-toolbar button[name='codeview']").click();
    expect("[name='txt'] .odoo-editor-editable").toHaveClass("d-none");
    expect("[name='txt'] textarea").toHaveValue("<p>first</p>");

    // Switch to editor
    await contains(".o_codeview_btn").click();
    expect("[name='txt'] .odoo-editor-editable").toHaveInnerHTML("<p> first </p>");
    expect("[name='txt'] textarea").toHaveCount(0);
});

test("edit and enable/disable codeview with editor toolbar", async () => {
    patchWithCleanup(odoo, { debug: true });
    onRpc("partner", "web_save", ({ args }) => {
        expect(args[1].txt).toBe("<div></div>");
        expect.step("web_save");
    });
    await mountView({
        type: "form",
        resId: 1,
        resIds: [1, 2],
        resModel: "partner",
        arch: `
            <form>
                <field name="txt" widget="html" options="{'codeview': true}"/>
            </form>`,
    });

    setSelectionInHtmlField();
    await insertText(htmlEditor, "Hello ");
    expect("[name='txt'] .odoo-editor-editable").toHaveInnerHTML("<p>Hello first </p>");

    // Switch to code view
    const node = queryOne(".odoo-editor-editable p");
    setSelection({ anchorNode: node, anchorOffset: 0, focusNode: node, focusOffset: 1 });
    await waitFor(".o-we-toolbar");
    await contains(".o-we-toolbar button[name='codeview']").click();
    expect("[name='txt'] textarea").toHaveValue("<p>Hello first</p>");

    await contains("[name='txt'] textarea").edit("<p>Yop</p>");
    expect("[name='txt'] textarea").toHaveValue("<p>Yop</p>");

    // Switch to editor
    await contains(".o_codeview_btn").click();
    expect("[name='txt'] .odoo-editor-editable").toHaveInnerHTML("<p> Yop </p>");

    undo(htmlEditor);
    expect("[name='txt'] .odoo-editor-editable").toHaveInnerHTML("<p>Hello first </p>");

    undo(htmlEditor);
    expect("[name='txt'] .odoo-editor-editable").toHaveInnerHTML("<p>Hellofirst </p>");
});

test("edit and save a html field in collaborative should keep the same wysiwyg", async () => {
    patchWithCleanup(Wysiwyg.prototype, {
        setup() {
            super.setup();
            expect.step("Setup Wysiwyg");
        },
    });

    onRpc("partner", "web_save", ({ args }) => {
        const txt = args[1].txt;
        expect(normalizeHTML(txt, stripHistoryIds)).toBe("<p>Hello first</p>");
        expect.step("web_save");
        args[1].txt = txt.replace(
            /\sdata-last-history-steps="[^"]*?"/,
            ' data-last-history-steps="12345"'
        );
    });
    onRpc("/html_editor/get_ice_servers", () => {
        return [];
    });
    onRpc("/html_editor/bus_broadcast", (params) => {
        return { id: 10 };
    });

    await mountView({
        type: "form",
        resId: 1,
        resModel: "partner",
        arch: `
            <form>
                <field name="txt" widget="html" options="{'collaborative': true}"/>
            </form>`,
    });

    setSelectionInHtmlField();
    await insertText(htmlEditor, "Hello ");
    expect("[name='txt'] .odoo-editor-editable").toHaveInnerHTML("<p>Hello first </p>");
    expect.verifySteps(["Setup Wysiwyg"]);

    await clickSave();
    expect.verifySteps(["web_save"]);
});

describe("sandbox", () => {
    const recordWithComplexHTML = {
        id: 1,
        txt: `
    <!DOCTYPE HTML>
    <html xml:lang="en" lang="en">
        <head>
            <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
            <meta name="format-detection" content="telephone=no"/>
            <style type="text/css">
                body {
                    color: blue;
                }
            </style>
        </head>
        <body>
            Hello
        </body>
    </html>
    `,
    };

    function getSandboxContent(content) {
        return `
        <!DOCTYPE HTML>
        <html xml:lang="en" lang="en">
            <head>
                <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
                <meta name="format-detection" content="telephone=no"/>
                <style type="text/css"></style>
            </head>
            <body>
                ${content}
            </body>
        </html>
        `;
    }
    test("complex html is automatically in sandboxed preview mode", async () => {
        Partner._records = [recordWithComplexHTML];
        await mountView({
            type: "form",
            resId: 1,
            resModel: "partner",
            arch: `
                <form>
                    <field name="txt" widget="html"/>
                </form>`,
        });
        expect(
            `.o_field_html[name="txt"] iframe[sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"]`
        ).toHaveCount(1);
    });

    test("readonly sandboxed preview", async () => {
        Partner._records = [recordWithComplexHTML];
        await mountView({
            type: "form",
            resId: 1,
            resModel: "partner",
            arch: `
                <form string="Partner">
                    <field name="txt" widget="html" readonly="1" options="{'sandboxedPreview': true}"/>
                </form>`,
        });

        const readonlyIframe = queryOne(
            '.o_field_html[name="txt"] iframe[sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"]'
        );
        expect(readonlyIframe.contentDocument.body).toHaveText("Hello");
        expect(
            readonlyIframe.contentWindow.getComputedStyle(readonlyIframe.contentDocument.body).color
        ).toBe("rgb(0, 0, 255)");
        expect("#codeview-btn-group > button").toHaveCount(0, {
            message: "Codeview toggle should not be possible in readonly mode.",
        });
    });

    function htmlDocumentTextTemplate(text, color) {
        return `
        <html>
            <head>
                <style>
                    body {
                        color: ${color};
                    }
                </style>
            </head>
            <body>
                ${text}
            </body>
        </html>
        `;
    }

    test("sandboxed preview display and editing", async () => {
        Partner._records = [
            {
                id: 1,
                txt: htmlDocumentTextTemplate("Hello", "red"),
            },
        ];
        onRpc("partner", "web_save", ({ args }) => {
            expect(args[1].txt).toBe(htmlDocumentTextTemplate("Hi", "blue"));
            expect.step("web_save");
        });
        await mountView({
            type: "form",
            resId: 1,
            resModel: "partner",
            arch: `
                <form>
                    <sheet>
                        <notebook>
                                <page string="Body" name="body">
                                    <field name="txt" widget="html" options="{'sandboxedPreview': true}"/>
                                </page>
                        </notebook>
                    </sheet>
                </form>`,
        });

        // check original displayed content
        let iframe = queryOne(
            '.o_field_html[name="txt"] iframe[sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"]'
        );
        expect(`.o_form_button_save`).not.toBeVisible();
        expect(iframe.contentDocument.body).toHaveText("Hello");
        expect(
            iframe.contentDocument.head.querySelector("style").textContent.trim().replace(/\s/g, "")
        ).toBe("body{color:red;}", {
            message: "Head nodes should remain unaltered in the head",
        });
        expect(iframe.contentWindow.getComputedStyle(iframe.contentDocument.body).color).toBe(
            "rgb(255, 0, 0)"
        );
        expect("#codeview-btn-group > button").toHaveCount(1);

        // switch to XML editor and edit
        await contains("#codeview-btn-group > button").click();
        expect('.o_field_html[name="txt"] textarea').toHaveCount(1);

        await contains('.o_field_html[name="txt"] textarea').edit(
            htmlDocumentTextTemplate("Hi", "blue")
        );
        expect(`.o_form_button_save`).toBeVisible();

        // check displayed content after edit
        await contains("#codeview-btn-group > button").click();
        iframe = queryOne(
            '.o_field_html[name="txt"] iframe[sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"]'
        );
        await animationFrame();
        expect(iframe.contentDocument.body).toHaveText("Hi");
        expect(
            iframe.contentDocument.head.querySelector("style").textContent.trim().replace(/\s/g, "")
        ).toBe("body{color:blue;}", {
            message: "Head nodes should remain unaltered in the head",
        });
        expect(iframe.contentWindow.getComputedStyle(iframe.contentDocument.body).color).toBe(
            "rgb(0, 0, 255)"
        );

        await contains(".o_form_button_save").click();
        expect.verifySteps(["web_save"]);
    });

    test("switch page after editing html with code editor", async () => {
        Partner._records = [
            {
                id: 1,
                txt: htmlDocumentTextTemplate("Hello", "red"),
            },
            {
                id: 2,
                txt: htmlDocumentTextTemplate("Bye", "green"),
            },
        ];
        onRpc("partner", "web_save", ({ args }) => {
            expect(args[1].txt).toBe(htmlDocumentTextTemplate("Hi", "blue"));
            expect.step("web_save");
        });
        await mountView({
            type: "form",
            resId: 1,
            resIds: [1, 2],
            resModel: "partner",
            arch: `
                <form>
                    <sheet>
                        <notebook>
                                <page string="Body" name="body">
                                    <field name="txt" widget="html" options="{'sandboxedPreview': true}"/>
                                </page>
                        </notebook>
                    </sheet>
                </form>`,
        });

        // switch to XML editor and edit
        await contains("#codeview-btn-group > button").click();
        expect('.o_field_html[name="txt"] textarea').toHaveValue(
            htmlDocumentTextTemplate("Hello", "red")
        );

        await contains('.o_field_html[name="txt"] textarea').edit(
            htmlDocumentTextTemplate("Hi", "blue")
        );
        expect(`.o_form_button_save`).toBeVisible();
        expect('.o_field_html[name="txt"] textarea').toHaveValue(
            htmlDocumentTextTemplate("Hi", "blue")
        );

        await contains(`.o_pager_next`).click();
        expect.verifySteps(["web_save"]);
        expect(`.o_form_button_save`).not.toBeVisible();
        expect('.o_field_html[name="txt"] textarea').toHaveValue(
            htmlDocumentTextTemplate("Bye", "green")
        );

        await contains(`.o_pager_previous`).click();
        expect('.o_field_html[name="txt"] textarea').toHaveValue(
            htmlDocumentTextTemplate("Hi", "blue")
        );
    });

    test("sanboxed preview mode not automatically enabled for regular values", async () => {
        Partner._records = [
            {
                id: 1,
                txt: `
                <body>
                    <p>Hello</p>
                </body>
            `,
            },
        ];

        await mountView({
            type: "form",
            resId: 1,
            resModel: "partner",
            arch: `
                <form>
                    <field name="txt" widget="html"/>
                </form>`,
        });
        expect(`.o_field_html[name="txt"] iframe[sandbox]`).toHaveCount(0);
        expect(`.o_field_html[name="txt"] iframe[sandbox]`).toHaveCount(0);
    });

    test("sandboxed preview option applies even for simple text", async () => {
        Partner._records = [
            {
                id: 1,
                txt: `
                    Hello
                `,
            },
        ];
        await mountView({
            type: "form",
            resId: 1,
            resModel: "partner",
            arch: `
                    <form>
                    <field name="txt" widget="html" options="{'sandboxedPreview': true}"/>
                    </form>`,
        });
        expect(
            `.o_field_html[name="txt"] iframe[sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"]`
        ).toHaveCount(1);
    });

    test("links should open on a new tab in sandboxedPreview", async () => {
        Partner._records = [
            {
                id: 1,
                txt: getSandboxContent(`
                    <div>
                        <p>first</p>
                        <a href="/contactus">Relative link</a>
                        <a href="${browser.location.origin}/contactus">Internal link</a>
                        <a href="https://google.com">External link</a>
                    </div>`),
            },
            {
                id: 2,
                txt: getSandboxContent(`
                    <div>
                        <p>second</p>
                        <a href="/contactus2">Relative link</a>
                        <a href="${browser.location.origin}/contactus2">Internal link</a>
                        <a href="https://google2.com">External link</a>
                    </div>`),
            },
        ];

        await mountView({
            type: "form",
            resId: 1,
            resIds: [1, 2],
            resModel: "partner",
            arch: `
                <form>
                    <field name="txt" widget="html" readonly="1" options="{'sandboxedPreview': true}"/>
                </form>`,
        });

        let readonlyIframe = queryOne('.o_field_html[name="txt"] iframe');
        expect(readonlyIframe.contentDocument.body.querySelector("p")).toHaveText("first");
        for (const link of readonlyIframe.contentDocument.body.querySelectorAll("a")) {
            expect(link.getAttribute("target")).toBe("_blank");
            expect(link.getAttribute("rel")).toBe("noreferrer");
        }

        await contains(`.o_pager_next`).click();
        readonlyIframe = queryOne('.o_field_html[name="txt"] iframe');
        expect(readonlyIframe.contentDocument.body.querySelector("p")).toHaveText("second");
        for (const link of readonlyIframe.contentDocument.body.querySelectorAll("a")) {
            expect(link.getAttribute("target")).toBe("_blank");
            expect(link.getAttribute("rel")).toBe("noreferrer");
        }
    });

    test("html field in readonly updated by onchange in sandboxedPreview", async () => {
        Partner._records = [{ id: 1, name: "first", txt: getSandboxContent("<p>first</p>") }];
        Partner._onChanges = {
            name(record) {
                record.txt = getSandboxContent(`<p>${record.name}</p>`);
            },
        };
        await mountView({
            type: "form",
            resId: 1,
            resIds: [1, 2],
            resModel: "partner",
            arch: `
                <form>
                    <field name="name"/>
                    <field name="txt" widget="html" readonly="1"/>
                </form>`,
        });

        let readonlyIframe = queryOne('.o_field_html[name="txt"] iframe');
        expect(readonlyIframe.contentDocument.body).toHaveInnerHTML(`<p>first</p>`);

        await contains(`.o_field_widget[name=name] input`).edit("hello");
        readonlyIframe = queryOne('.o_field_html[name="txt"] iframe');
        expect(readonlyIframe.contentDocument.body).toHaveInnerHTML(`<p>hello</p>`);
    });

    test("readonly with cssReadonly", async () => {
        Partner._records = [
            {
                id: 1,
                txt: `<p>Hello</p>
        `,
            },
        ];

        patchWithCleanup(assets, {
            async getBundle(name) {
                expect.step(name);
                return {
                    cssLibs: ["testCSS"],
                    jsLibs: [],
                };
            },
        });

        await mountView({
            type: "form",
            resId: 1,
            resModel: "partner",
            arch: `
                <form string="Partner">
                    <field name="txt" widget="html" readonly="1" options="{'cssReadonly': 'template.assets'}"/>
                </form>`,
        });

        const readonlyIframe = queryOne('.o_field_html[name="txt"] iframe');
        expect(
            readonlyIframe.contentDocument.head.querySelector(`link[href='testCSS']`)
        ).toHaveCount(1);
        expect(readonlyIframe.contentDocument.body).toHaveInnerHTML(
            `<div id="iframe_target"> <p> Hello </p> </div>`
        );
        expect.verifySteps(["template.assets"]);
    });

    test("click on next/previous page when readonly with cssReadonly ", async () => {
        await mountView({
            type: "form",
            resId: 1,
            resIds: [1, 2],
            resModel: "partner",
            arch: `
                <form string="Partner">
                    <field name="txt" widget="html" readonly="1" options="{'cssReadonly': 'template.assets'}"/>
                </form>`,
        });

        let readonlyIframe = queryOne('.o_field_html[name="txt"] iframe');
        expect(readonlyIframe.contentDocument.body).toHaveInnerHTML(
            `<div id="iframe_target"> <p> first </p> </div>`
        );

        await contains(`.o_pager_next`).click();
        readonlyIframe = queryOne('.o_field_html[name="txt"] iframe');
        expect(readonlyIframe.contentDocument.body).toHaveInnerHTML(
            `<div id="iframe_target"> <p> second </p> </div>`
        );
    });
});

describe("direction config", () => {
    test("ltr direction", async () => {
        defineParams({
            lang_parameters: {
                direction: "ltr",
            },
        });
        await mountView({
            type: "form",
            resId: 1,
            resModel: "partner",
            arch: `
            <form>
                <field name="txt" widget="html"/>
            </form>`,
        });
        expect(".odoo-editor-editable").toHaveAttribute("dir", "ltr");
        const node = queryOne(".odoo-editor-editable p");
        setSelection({ anchorNode: node.firstChild, anchorOffset: 0 });
        await insertText(htmlEditor, "/Switchdirection");
        await animationFrame();
        expect(queryAllTexts(".o-we-command-name")).toEqual(["Switch direction"]);
        await press("Enter");
        expect(".odoo-editor-editable p").toHaveAttribute("dir", "rtl");
    });

    test("rtl direction", async () => {
        defineParams({
            lang_parameters: {
                direction: "rtl",
            },
        });
        await mountView({
            type: "form",
            resId: 1,
            resModel: "partner",
            arch: `
            <form>
                <field name="txt" widget="html"/>
            </form>`,
        });
        expect(".odoo-editor-editable").toHaveAttribute("dir", "rtl");
        const node = queryOne(".odoo-editor-editable p");
        setSelection({ anchorNode: node.firstChild, anchorOffset: 0 });
        await insertText(htmlEditor, "/Switchdirection");
        await animationFrame();
        expect(queryAllTexts(".o-we-command-name")).toEqual(["Switch direction"]);
        await press("Enter");
        expect(".odoo-editor-editable p").toHaveAttribute("dir", "ltr");
    });
});

describe("save image", () => {
    function pasteFile(editor, file) {
        const clipboardData = new DataTransfer();
        clipboardData.items.add(file);
        const pasteEvent = new ClipboardEvent("paste", { clipboardData, bubbles: true });
        editor.editable.dispatchEvent(pasteEvent);
    }

    function createBase64ImageFile(base64ImageData) {
        const binaryImageData = atob(base64ImageData);
        const uint8Array = new Uint8Array(binaryImageData.length);
        for (let i = 0; i < binaryImageData.length; i++) {
            uint8Array[i] = binaryImageData.charCodeAt(i);
        }
        return new File([uint8Array], "test_image.png", { type: "image/png" });
    }

    test("Ensure that urgentSave works even with modified image to save", async () => {
        expect.assertions(5);
        Partner._records = [
            {
                id: 1,
                txt: "<p class='test_target'><br></p>",
            },
        ];
        let sendBeaconDef;
        mockSendBeacon((route, blob) => {
            blob.text().then((r) => {
                const { params } = JSON.parse(r);
                const { args, model } = params;
                if (route === "/web/dataset/call_kw/partner/web_save" && model === "partner") {
                    if (writeCount === 0) {
                        // Save normal value without image.
                        expect(args[1].txt).toBe(`<p class="test_target">a<br></p>`);
                    } else if (writeCount === 1) {
                        // Save image with unfinished modification changes.
                        expect(args[1].txt).toBe(imageContainerHTML);
                    } else if (writeCount === 2) {
                        // Save the modified image.
                        expect(args[1].txt).toBe(getImageContainerHTML(newImageSrc, false));
                    } else {
                        // Fail the test if too many write are called.
                        expect(true).toBe("false");
                        throw new Error("Write should only be called 3 times during this test");
                    }
                    writeCount += 1;
                }
                sendBeaconDef.resolve();
            });
            return true;
        });

        let formController;
        // Patch to get the controller instance.
        patchWithCleanup(FormController.prototype, {
            setup() {
                super.setup(...arguments);
                formController = this;
            },
        });

        const imageRecord = IrAttachment._records[0];
        // Method to get the html of a cropped image.
        const getImageContainerHTML = (src, isModified) => {
            return `
            <p>
                <img
                    class="img img-fluid o_we_custom_image o_we_image_cropped${
                        isModified ? " o_modified_image_to_save" : ""
                    }"
                    data-original-id="${imageRecord.id}"
                    data-original-src="${imageRecord.image_src}"
                    data-mimetype="image/png"
                    data-width="50"
                    data-height="50"
                    data-scale-x="1"
                    data-scale-y="1"
                    data-aspect-ratio="0/0"
                    src="${src}"
                >
                <br>
            </p>
        `
                .replace(/(?:\s|(?:\r\n))+/g, " ")
                .replace(/\s?(<|>)\s?/g, "$1");
        };
        // Promise to resolve when we want the response of the modify_image RPC.
        const modifyImagePromise = new Deferred();
        let writeCount = 0;
        let modifyImageCount = 0;
        // Valid base64 encoded image in its transitory modified state.
        const imageContainerHTML = getImageContainerHTML(
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII",
            true
        );
        // New src URL to assign to the image when the modification is
        // "registered".
        const newImageSrc = "/web/image/1234/cropped_transparent.png";
        onRpc("web_save", () => {
            expect(true).toBe(false);
            throw new Error("web_save should only be called through sendBeacon");
        });
        onRpc(`/html_editor/modify_image/${imageRecord.id}`, async (request) => {
            if (modifyImageCount === 0) {
                const { params } = await request.json();
                expect(params.res_model).toBe("partner");
                expect(params.res_id).toBe(1);
                await modifyImagePromise;
                modifyImageCount++;
                return newImageSrc;
            } else {
                // Fail the test if too many modify_image are called.
                expect(true).toBe(false);
                throw new Error("The image should only have been modified once during this test");
            }
        });
        await mountView({
            type: "form",
            resId: 1,
            resModel: "partner",
            arch: `
            <form>
                <field name="txt" widget="html"/>
            </form>`,
        });

        // Simulate an urgent save without any image in the content.
        sendBeaconDef = new Deferred();
        setSelectionInHtmlField(".test_target");
        await insertText(htmlEditor, "a");
        htmlEditor.shared.history.addStep();
        await formController.beforeUnload();
        await sendBeaconDef;

        // Replace the empty paragraph with a paragrah containing an unsaved
        // modified image
        const imageContainerElement = parseHTML(htmlEditor.document, imageContainerHTML).firstChild;
        const paragraph = htmlEditor.editable.querySelector(".test_target");
        htmlEditor.editable.replaceChild(imageContainerElement, paragraph);
        htmlEditor.shared.history.addStep();

        // Simulate an urgent save before the end of the RPC roundtrip for the
        // image.
        sendBeaconDef = new Deferred();
        await formController.beforeUnload();
        await sendBeaconDef;

        // Resolve the image modification (simulate end of RPC roundtrip).
        modifyImagePromise.resolve();
        await modifyImagePromise;
        await animationFrame();

        // Simulate the last urgent save, with the modified image.
        sendBeaconDef = new Deferred();
        await formController.beforeUnload();
        await sendBeaconDef;
    });

    test("Pasted/dropped images are converted to attachments on save", async () => {
        Partner._records = [
            {
                id: 1,
                txt: "<p class='test_target'><br></p>",
            },
        ];
        onRpc("/html_editor/attachment/add_data", async (request) => {
            const { params } = await request.json();
            const { res_id, res_model } = params;
            expect.step(`add_data: ${res_model} ${res_id}`);
            return {
                image_src: "/test_image_url.png",
                access_token: "1234",
                public: false,
            };
        });

        await mountView({
            type: "form",
            resId: 1,
            resModel: "partner",
            arch: `
                <form>
                    <field name="txt" widget="html"/>
                </form>`,
        });
        setSelectionInHtmlField(".test_target");

        // Paste image.
        pasteFile(
            htmlEditor,
            createBase64ImageFile(
                "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII"
            )
        );
        await waitFor("img");
        const img = htmlEditor.editable.querySelector("img");
        expect(img.src.startsWith("data:image/png;base64,")).toBe(true);
        expect(img).toHaveClass("o_b64_image_to_save");

        // Save changes.
        await contains(".o_form_button_save").click();
        expect(img.getAttribute("src")).toBe("/test_image_url.png?access_token=1234");
        expect(img).not.toHaveClass("o_b64_image_to_save");
        expect.verifySteps(["add_data: partner 1"]);
    });

    test("Pasted/dropped images are converted once to attachments on save with slow network", async () => {
        Partner._records = [
            {
                id: 1,
                txt: "<p class='test_target'><br></p>",
            },
        ];

        const def = new Deferred();
        onRpc("/html_editor/attachment/add_data", async (request) => {
            const { params } = await request.json();
            const { res_id, res_model } = params;
            expect.step(`add_data-start: ${res_model} ${res_id}`);
            await def;
            expect.step(`add_data-end: ${res_model} ${res_id}`);
            return {
                image_src: "/test_image_url.png",
                access_token: "1234",
                public: false,
            };
        });

        onRpc("partner", "web_save", ({ args }) => {
            expect.step("web_save");
            expect(args[1].txt).toBe(
                `<p class="test_target"><img class="img-fluid" data-file-name="test_image.png" src="/test_image_url.png?access_token=1234"></p>`
            );
        });

        await mountView({
            type: "form",
            resId: 1,
            resModel: "partner",
            arch: `
                <form>
                    <field name="txt" widget="html"/>
                </form>`,
        });
        setSelectionInHtmlField(".test_target");

        // Paste image.
        pasteFile(
            htmlEditor,
            createBase64ImageFile(
                "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII"
            )
        );
        await waitFor("img");
        const img = htmlEditor.editable.querySelector("img");
        expect(img.src.startsWith("data:image/png;base64,")).toBe(true);
        expect(img).toHaveClass("o_b64_image_to_save");

        // Save changes.
        await contains(".o_form_button_save").click();
        expect(img.src.startsWith("data:image/png;base64,")).toBe(true);
        expect(img).toHaveClass("o_b64_image_to_save");

        def.resolve();
        await tick();
        expect(img.getAttribute("src")).toBe("/test_image_url.png?access_token=1234");
        expect(img).not.toHaveClass("o_b64_image_to_save");

        expect.verifySteps(["add_data-start: partner 1", "add_data-end: partner 1", "web_save"]);
    });

    test("Pasted/dropped images are converted once to attachments on switch page with slow network", async () => {
        Partner._records = [
            {
                id: 1,
                txt: "<p class='test_target'><br></p>",
            },
            {
                id: 2,
                txt: "<p class='test_target_2'><br></p>",
            },
        ];

        const def = new Deferred();
        onRpc("/html_editor/attachment/add_data", async (request) => {
            const { params } = await request.json();
            const { res_id, res_model } = params;
            expect.step(`add_data-start: ${res_model} ${res_id}`);
            await def;
            expect.step(`add_data-end: ${res_model} ${res_id}`);
            return {
                image_src: "/test_image_url.png",
                access_token: "1234",
                public: false,
            };
        });

        onRpc("partner", "web_save", ({ args }) => {
            expect.step("web_save");
            expect(args[1].txt).toBe(
                `<p class="test_target"><img class="img-fluid" data-file-name="test_image.png" src="/test_image_url.png?access_token=1234"></p>`
            );
        });

        await mountView({
            type: "form",
            resId: 1,
            resIds: [1, 2],
            resModel: "partner",
            arch: `
                <form>
                    <field name="txt" widget="html"/>
                </form>`,
        });
        setSelectionInHtmlField(".test_target");

        // Paste image.
        pasteFile(
            htmlEditor,
            createBase64ImageFile(
                "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII"
            )
        );
        await waitFor("img");
        const img = htmlEditor.editable.querySelector("img");
        expect(img.src.startsWith("data:image/png;base64,")).toBe(true);
        expect(img).toHaveClass("o_b64_image_to_save");

        // Save changes.
        await contains(".o_pager_next").click();
        expect(img.src.startsWith("data:image/png;base64,")).toBe(true);
        expect(img).toHaveClass("o_b64_image_to_save");
        expect(".test_target_2").toHaveCount(0);

        def.resolve();
        await animationFrame();

        expect(".test_target_2").toHaveCount(1);
        expect.verifySteps(["add_data-start: partner 1", "add_data-end: partner 1", "web_save"]);
    });

    test("Pasted/dropped images are converted to attachments without access_token on save", async () => {
        Partner._records = [
            {
                id: 1,
                txt: "<p class='test_target'><br></p>",
            },
        ];
        onRpc("/html_editor/attachment/add_data", async (request) => {
            const { params } = await request.json();
            const { res_id, res_model } = params;
            expect.step(`add_data: ${res_model} ${res_id}`);
            return {
                image_src: "/test_image_url.png",
                id: 123,
                public: false,
            };
        });

        onRpc("ir.attachment", "generate_access_token", ({ args }) => {
            expect.step(`generate_access_token: ${args}`);
            return ["12345"];
        });

        await mountView({
            type: "form",
            resId: 1,
            resModel: "partner",
            arch: `
                <form>
                    <field name="txt" widget="html"/>
                </form>`,
        });
        setSelectionInHtmlField(".test_target");

        // Paste image.
        pasteFile(
            htmlEditor,
            createBase64ImageFile(
                "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII"
            )
        );
        await waitFor("img");
        const img = htmlEditor.editable.querySelector("img");
        expect(img.src.startsWith("data:image/png;base64,")).toBe(true);
        expect(img).toHaveClass("o_b64_image_to_save");

        // Save changes.
        await contains(".o_form_button_save").click();
        expect(img.getAttribute("src")).toBe("/test_image_url.png?access_token=12345");
        expect(img).not.toHaveClass("o_b64_image_to_save");
        expect.verifySteps(["add_data: partner 1", "generate_access_token: 123"]);
    });
});

describe("translatable", () => {
    test("should display translate button when html field is translatable", async () => {
        Partner._fields.txt = fields.Html({ string: "txt", translate: true });
        serverState.lang = "en_US";
        serverState.multiLang = true;

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

        expect(".o_field_html .btn.o_field_translate").not.toBeVisible();

        // Focus on the editable to make the translate button visible
        await contains(".odoo-editor-editable").click();
        expect(".o_field_html .btn.o_field_translate").toBeVisible();

        // Click away to remove focus
        await contains(".o_form_label").click();
        expect(".o_field_html .btn.o_field_translate").not.toBeVisible();
    });
});
