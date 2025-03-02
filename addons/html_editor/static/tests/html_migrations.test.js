import { HtmlField } from "@html_editor/fields/html_field";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import {
    defineModels,
    fields,
    models,
    mountView,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    txt = fields.Html({ trim: true });
    name = fields.Char();

    _records = [
        {
            id: 1,
            name: "first",
            txt: `<p>Hello World</p><div data-embedded="draw" data-embedded-props='{"source": "https://excalidraw.com"}'/>`,
        },
    ];
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
            await mountView({
                type: "form",
                resId: 1,
                resModel: "partner",
                arch: `
                    <form>
                        <field name="txt" widget="html"/>
                    </form>`,
            });
            expect("[data-embedded='draw']").toHaveCount(0);
            expect("a[href='https://excalidraw.com']").toHaveCount(1);
            expect(htmlFieldComponent.editor.getContent()).toBe(
                `<p data-oe-version="1.1">Hello World</p><p><a href="https://excalidraw.com">https://excalidraw.com</a></p>`
            );
        });
    });

    describe("In html viewer", () => {
        test("Excalidraw EmbeddedComponent is replaced by a link (readonly)", async () => {
            await mountView({
                type: "form",
                resId: 1,
                resModel: "partner",
                arch: `
                    <form>
                        <field name="txt" widget="html" readonly="1"/>
                    </form>`,
            });
            expect("[data-embedded='draw']").toHaveCount(0);
            expect("a[href='https://excalidraw.com']").toHaveCount(1);
        });
    });
});
