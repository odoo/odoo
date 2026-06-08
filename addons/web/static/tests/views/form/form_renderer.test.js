import { expect, test } from "@odoo/hoot";
import { queryAllTexts, queryOne } from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";
import { defineModels, fields, models, mountView, contains } from "@web/../tests/web_test_helpers";

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
    expect.verifySteps(["setup field component"]);
});

test.tags("desktop");
test("compile a button with id on desktop", async () => {
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

test.tags("mobile");
test("compile a button with id on mobile", async () => {
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
    await contains(`.o_cp_action_menus button:has(.fa-cog)`).click();
    expect(`button[id=action_button]`).toHaveCount(1);
});

test("compile a button with disabled", async () => {
    Partner._views = {
        form: /*xml*/ `
            <form>
                <button id="action_button" string="ActionButton" name="action_button" type="object" disabled="disabled"/>
            </form>
        `,
    };

    await mountView({
        resModel: "partner",
        type: "form",
        resId: 1,
    });
    expect(`button[id=action_button]`).toHaveAttribute("disabled");
});

test.tags("desktop");
test("statusbar stay visible when scrolling (sticky)", async () => {
    Partner._views = {
        form: /*xml*/ `
            <form>
                <header>
                    <button id="action_button" string="ActionButton"/>
                </header>
                <sheet>
                    <h2>My Sheet</h2>
                    <div class="position-relative" style="height: 200vh"></div>
                </sheet>
            </form>
        `,
    };

    await mountView({
        resModel: "partner",
        type: "form",
        resId: 1,
    });

    const statusBar = queryOne(".o_form_view .o_form_statusbar");

    const scrollTarget = queryOne(".o_form_view .o_content");
    const scrollRect = scrollTarget.getBoundingClientRect();
    expect(statusBar.getBoundingClientRect().top).toBeWithin(scrollRect.top, scrollRect.bottom);
    scrollTarget.scrollTop = scrollTarget.scrollHeight; // scroll to bottom
    expect(statusBar.getBoundingClientRect().top).toBeWithin(scrollRect.top, scrollRect.bottom);
});

test.tags("mobile");
test("statusbar is non-sticky on mobile", async () => {
    Partner._views = {
        form: /*xml*/ `
            <form>
                <header>
                    <button id="action_button" string="ActionButton"/>
                </header>
                <sheet>
                    <h2>My Sheet</h2>
                    <div class="position-relative" style="height: 200vh"></div>
                </sheet>
            </form>
        `,
    };

    await mountView({
        resModel: "partner",
        type: "form",
        resId: 1,
    });

    const statusBar = queryOne(".o_form_view .o_form_statusbar");

    const scrollTarget = queryOne(".o_form_view .o_form_view_container");
    const scrollRect = scrollTarget.getBoundingClientRect();
    expect(statusBar.getBoundingClientRect().top).toBeWithin(scrollRect.top, scrollRect.bottom);
    scrollTarget.scrollTop = scrollTarget.scrollHeight; // scroll to bottom
    expect(statusBar.getBoundingClientRect().top).not.toBeWithin(scrollRect.top, scrollRect.bottom);
});
