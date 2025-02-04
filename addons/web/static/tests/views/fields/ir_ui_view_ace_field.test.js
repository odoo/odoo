import { expect, test, describe } from "@odoo/hoot";

import {
    defineModels,
    fields,
    models,
    mountView,
    preloadBundle,
    preventResizeObserverError,
} from "@web/../tests/web_test_helpers";

const INVALID_XPATH = ".invalid_xpath";

class IrUiView extends models.Model {
    _name = "ir.ui.view";
    _rec_name = "name";

    name = fields.Char({ required: true });
    arch = fields.Text({});
    invalid_xpaths_from_arch = fields.Json();

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
            invalid_xpaths_from_arch: false,
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
                <field name="invalid_xpaths_from_arch"/>
                <field name="arch" widget="code_ir_ui_view" options='{"mode": "xml"}'/>
            </form>
        `,
    });

describe("Highlight invalid xpaths in inherited ir.ui.view", () => {
    test("with no invalid xpaths", async () => {
        await mountChildView();
        expect(INVALID_XPATH).toHaveCount(0);
    });

    test("with invalid xpaths", async () => {
        const invalid_xpaths_from_arch = [
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
        IrUiView._records[0].invalid_xpaths_from_arch = invalid_xpaths_from_arch;
        await mountChildView();
        expect(INVALID_XPATH).toHaveCount(invalid_xpaths_from_arch.length);
    });
});
