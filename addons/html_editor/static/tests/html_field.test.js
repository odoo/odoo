import { HtmlField } from "@html_editor/fields/html_field";
import { beforeEach, expect, test } from "@odoo/hoot";
import { click, press, queryOne } from "@odoo/hoot-dom";
import { animationFrame, tick } from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { setSelection } from "./_helpers/selection";
import { insertText } from "./_helpers/user_actions";

class Partner extends models.Model {
    txt = fields.Html({ trim: true });

    _records = [
        { id: 1, txt: "<p>first</p>" },
        { id: 2, txt: "<p>second</p>" },
    ];
}
defineModels([Partner]);

let htmlEditor;
beforeEach(() => {
    patchWithCleanup(HtmlField.prototype, {
        onLoad(editor) {
            htmlEditor = editor;
            return super.onLoad(...arguments);
        },
    });
});

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

    const anchorNode = queryOne(".odoo-editor-editable p");
    setSelection({ anchorNode, anchorOffset: 0 });
    insertText(htmlEditor, "test");
    await animationFrame();
    expect(".odoo-editor-editable p").toHaveText("testfirst");
    expect(".o_form_button_save").toBeVisible();

    await contains(".o_form_button_save").click();
    expect(["web_save"]).toVerifySteps();
    expect(".odoo-editor-editable p").toHaveText("testfirst");
    expect(`.o_form_button_save`).not.toBeVisible();
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

    const anchorNode = queryOne(".odoo-editor-editable p");
    setSelection({ anchorNode, anchorOffset: 0 });
    insertText(htmlEditor, "test");
    await animationFrame();
    expect(".odoo-editor-editable p").toHaveText("testfirst");
    expect(`.o_form_button_save`).toBeVisible();

    await contains(`.o_pager_next`).click();
    await animationFrame();
    expect(".odoo-editor-editable p").toHaveText("second");
    expect(`.o_form_button_save`).not.toBeVisible();
    expect(["web_save"]).toVerifySteps();

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
    click(".odoo-editor-editable");
    const anchorNode = queryOne(".odoo-editor-editable p");
    setSelection({ anchorNode, anchorOffset: 0 });
    insertText(htmlEditor, "test");
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
    click(".odoo-editor-editable");
    const anchorNode = queryOne(".odoo-editor-editable p");
    setSelection({ anchorNode, anchorOffset: 0 });
    insertText(htmlEditor, "test");
    await animationFrame();
    expect(".odoo-editor-editable p").toHaveText("testfirst");
    expect(`.o_form_button_cancel`).toBeVisible();

    press(["ctrl", "z"]);
    expect(".odoo-editor-editable p").toHaveText("tesfirst");
    expect(`.o_form_button_cancel`).toBeVisible();

    await contains(`.o_form_button_cancel`).click();
    await animationFrame();
    expect(".odoo-editor-editable p").toHaveText("first");
    expect(`.o_form_button_cancel`).not.toBeVisible();

    press(["ctrl", "z"]);
    expect(".odoo-editor-editable p").toHaveText("first");
    expect(`.o_form_button_cancel`).not.toBeVisible();
});

test.todo(
    "A new MediaDialog after switching record in a Form view should have the correct resId",
    async () => {
        Partner._records = [
            { id: 1, txt: "<p>first</p>" },
            { id: 2, txt: "<p>second</p>" },
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
        expect(".odoo-editor-editable p:contains(first)").toHaveCount();

        await contains(`.o_pager_next`).click();
        expect(".odoo-editor-editable p:contains(second)").toHaveCount();

        const paragrah = queryOne(".odoo-editor-editable p");
        setSelection({ anchorNode: paragrah, anchorOffset: 0 });
        insertText("/Image");
        // press("Enter")

        await tick();
    }
);
