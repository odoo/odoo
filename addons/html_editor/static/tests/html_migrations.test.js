import { HtmlField } from "@html_editor/fields/html_field";
import { htmlEditorVersions } from "@html_editor/html_migrations/html_migrations_utils";
import { beforeEach, describe, expect, getFixture, test } from "@odoo/hoot";
import {
    defineModels,
    fields,
    models,
    mountView,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

const VERSIONS = htmlEditorVersions();
const CURRENT_VERSION = VERSIONS.at(-1);

class Partner extends models.Model {
    txt = fields.Html({ trim: true });
    name = fields.Char();

    _records = [
        {
            id: 1,
            name: "excalidraw",
            txt: `<p>Hello World</p><div data-embedded="draw" data-embedded-props='{"source": "https://excalidraw.com"}'/>`,
        },
        {
            id: 2,
            name: "banner",
            txt: `
                <p>test</p>
                <div class="o_editor_banner user-select-none o_not_editable lh-1 d-flex align-items-center alert alert-info pb-0 pt-3">
                    <i class="o_editor_banner_icon mb-3 fst-normal">💡</i>
                    <div class="w-100 px-3 o_editable">
                        <p>content</p>
                    </div>
                </div>`,
        },
    ];
}

async function mountViewWithRecord({ resId, readonly }) {
    return mountView({
        type: "form",
        resId,
        resModel: "partner",
        arch: `
            <form>
                <field name="txt" widget="html"${readonly ? ' readonly="1"' : ""}/>
            </form>`,
    });
}

defineModels([Partner]);

describe("test the migration process", () => {
    let htmlFieldComponent;
    beforeEach(() => {
        patchWithCleanup(HtmlField.prototype, {
            setup() {
                super.setup();
                htmlFieldComponent = this;
            },
        });
    });

    describe("In html field", () => {
        test("Excalidraw EmbeddedComponent is replaced by a link (editable)", async () => {
            await mountViewWithRecord({ resId: 1 });
            expect("[data-embedded='draw']").toHaveCount(0);
            expect("a[href='https://excalidraw.com']").toHaveCount(1);
            expect(htmlFieldComponent.editor.getContent()).toBe(
                `<p data-oe-version="${CURRENT_VERSION}">Hello World</p><p><a href="https://excalidraw.com">https://excalidraw.com</a></p>`
            );
        });
        test("Banner classes are properly updated (editable)", async () => {
            await mountViewWithRecord({ resId: 2 });
            const fixture = getFixture();
            expect(fixture.querySelector(".odoo-editor-editable")).toHaveInnerHTML(
                `<p>test</p>
                <div class="o_editor_banner user-select-none lh-1 d-flex align-items-center alert alert-info pb-0 pt-3 o-contenteditable-false" data-oe-role="status" contenteditable="false" role="status">
                    <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="Banner Info" aria-label="Banner Info">💡</i>
                    <div class="w-100 px-3 o_editor_banner_content o-contenteditable-true" contenteditable="true">
                        <p>content</p>
                    </div>
                </div>
                <div class="o-paragraph" data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></div>`
            );
            expect(htmlFieldComponent.editor.getContent()).toBe(
                `<p data-oe-version="${CURRENT_VERSION}">test</p>
                <div class="o_editor_banner user-select-none lh-1 d-flex align-items-center alert alert-info pb-0 pt-3 o-contenteditable-false" data-oe-role="status">
                    <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="Banner Info">💡</i>
                    <div class="w-100 px-3 o_editor_banner_content o-contenteditable-true">
                        <p>content</p>
                    </div>
                </div>`
            );
        });
    });

    describe("In html viewer", () => {
        test("Excalidraw EmbeddedComponent is replaced by a link (readonly)", async () => {
            await mountViewWithRecord({ resId: 1, readonly: true });
            expect("[data-embedded='draw']").toHaveCount(0);
            expect("a[href='https://excalidraw.com']").toHaveCount(1);
        });
        test("Banner classes are properly updated (readonly)", async () => {
            await mountViewWithRecord({ resId: 2, readonly: true });
            const fixture = getFixture();
            expect(fixture.querySelector(".o_readonly")).toHaveInnerHTML(
                `<p>test</p>
                <div class="o_editor_banner user-select-none lh-1 d-flex align-items-center alert alert-info pb-0 pt-3 o-contenteditable-false" data-oe-role="status" role="status">
                    <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="Banner Info" aria-label="Banner Info">💡</i>
                    <div class="w-100 px-3 o_editor_banner_content o-contenteditable-true">
                        <p>content</p>
                    </div>
                </div>`
            );
        });
    });
});
