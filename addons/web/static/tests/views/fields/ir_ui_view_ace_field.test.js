import { expect, test, describe } from "@odoo/hoot";

import {
    defineModels,
    fields,
    models,
    mountView,
    preloadBundle,
    preventResizeObserverError,
} from "@web/../tests/web_test_helpers";

const INVALID_LOCATOR = ".invalid_locator";

class IrUiView extends models.Model {
    _name = "ir.ui.view";
    _rec_name = "name";

    name = fields.Char({ required: true });
    arch = fields.Text({});
    invalid_locators = fields.Json();

    _records = [
        {
            id: 1,
            name: "Child View",
            arch: `
<data>
    <xpath expr="//field[@name='name']" position="after"/>
    <xpath expr="//group" position="inside"/>
    <xpath expr="//field[@name='inherit_id']" position="replace"/>
    <xpath expr="//field[@name='non_existent_field']" position="after"/>
    <xpath expr="//nonexistent_tag" position="inside"/>
    <xpath expr="//field[@name='arch_invalid']" position="after"/>
    <field name="invalid" position="replace"/>
</data>
            `,
            invalid_locators: false,
        },
    ];
}
defineModels([IrUiView]);

// Preload necessary bundles and prevent ResizeObserver errors
preloadBundle("web.ace_lib");
preventResizeObserverError();

const mountChildView = async () =>
    await mountView({
        resModel: "ir.ui.view",
        resId: 1,
        type: "form",
        arch: `
            <form>
                <field name="invalid_locators"/>
                <field name="arch" widget="code_ir_ui_view" options='{"mode": "xml"}'/>
            </form>
        `,
    });

describe("Highlight invalid locators in inherited ir.ui.view", () => {
    test("with no invalid locators", async () => {
        await mountChildView();
        expect(INVALID_LOCATOR).toHaveCount(0);
    });

    test("with invalid locators", async () => {
        const invalid_locators = [
            {
                tag: "xpath",
                attrib: {
                    expr: "//field[@name='non_existent_field']",
                    position: "after",
                },
                sourceline: 6,
            },
            {
                tag: "xpath",
                attrib: {
                    expr: "//nonexistent_tag",
                    position: "inside",
                },
                sourceline: 7,
            },
            {
                tag: "xpath",
                attrib: {
                    expr: "//field[@name='arch_invalid']",
                    position: "after",
                },
                sourceline: 8,
            },
            {
                tag: "field",
                attrib: {
                    name: "invalid",
                    position: "replace",
                },
                sourceline: 9,
            },
        ];
        IrUiView._records[0].invalid_locators = invalid_locators;
        await mountChildView();
        expect(INVALID_LOCATOR).toHaveCount(invalid_locators.length);
    });
});
