import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";
import { defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

import { registry } from "@web/core/registry";

class Partner extends models.Model {
    name = fields.Char();
    charfield = fields.Char();

    _records = [{ id: 1, name: "firstRecord", charfield: "content of charfield" }];
}
defineModels([Partner]);

test("compile form with modifiers", async () => {
    Partner._views = {
        form: /*xml*/ `
            <form>
                <div invisible="display_name == uid">
                    <field name="charfield"/>
                </div>
                <field name="display_name" readonly="display_name == uid"/>
            </form>
        `,
    };

    await mountView({
        resModel: "partner",
        type: "form",
        resId: 1,
    });
    expect(`.o_form_editable input`).toHaveCount(2);
});

test("compile notebook with modifiers", async () => {
    Partner._views = {
        form: /*xml*/ `
            <form>
                <sheet>
                    <notebook>
                        <page name="p1" invisible="display_name == 'lol'"><field name="charfield"/></page>
                        <page name="p2"><field name="display_name"/></page>
                    </notebook>
                </sheet>
            </form>
        `,
    };

    await mountView({
        resModel: "partner",
        type: "form",
        resId: 1,
    });
    expect(queryAllTexts`.o_notebook_headers .nav-item`).toEqual(["p1", "p2"]);
});

test("compile header and buttons", async () => {
    Partner._views = {
        form: /*xml*/ `
            <form>
                <header>
                    <button string="ActionButton" class="oe_highlight" name="action_button" type="object"/>
                </header>
            </form>
        `,
    };

    await mountView({
        resModel: "partner",
        type: "form",
        resId: 1,
    });
    expect(`.o_statusbar_buttons button[name=action_button]:contains(ActionButton)`).toHaveCount(1);
});

test("render field with placeholder", async () => {
    registry.category("fields").add(
        "char",
        {
            component: class CharField extends Component {
                static props = ["*"];
                static template = xml`<div/>`;
                setup() {
                    expect.step("setup field component");
                    expect(this.props.placeholder).toBe("e.g. Contact's Name or //someinfo...");
                }
            },
            extractProps: ({ attrs }) => ({ placeholder: attrs.placeholder }),
        },
        { force: true }
    );

    Partner._views = {
        form: /*xml*/ `
            <form>
                <field name="display_name" placeholder="e.g. Contact's Name or //someinfo..." />
            </form>
        `,
    };

    await mountView({
        resModel: "partner",
        type: "form",
        resId: 1,
    });
    expect(["setup field component"]).toVerifySteps();
});

test("compile a button with id", async () => {
    Partner._views = {
        form: /*xml*/ `
            <form>
                <header>
                    <button id="action_button" string="ActionButton"/>
                </header>
            </form>
        `,
    };

    await mountView({
        resModel: "partner",
        type: "form",
        resId: 1,
    });
    expect(`button[id=action_button]`).toHaveCount(1);
});
