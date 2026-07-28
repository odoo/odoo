/** @odoo-module **/

import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { click, editInput, patchWithCleanup } from "@web/../tests/helpers/utils";

let serverData;

QUnit.module("sms button field", {
    beforeEach() {
        serverData = {
            models: {
                partner: {
                    fields: {
                        message: { string: "message", type: "text" },
                        foo: { string: "Foo", type: "char", default: "My little Foo Value" },
                        mobile: { string: "mobile", type: "text" },
                    },
                    records: [
                        {
                            id: 1,
                            message: "",
                            foo: "yop",
                            mobile: "+32494444444",
                        },
                        {
                            id: 2,
                            message: "",
                            foo: "bayou",
                        },
                    ],
                },
                visitor: {
                    fields: {
                        mobile: { string: "mobile", type: "text" },
                    },
                    records: [{ id: 1, mobile: "+32494444444" }],
                },
            },
        };
        setupViewRegistries();
    },
});
QUnit.test("Sms button in form view", async (assert) => {
    await makeView({
        type: "form",
        resModel: "visitor",
        resId: 1,
        serverData,
        arch: `
            <form>
                <sheet>
                    <field name="mobile" widget="phone"/>
                </sheet>
            </form>`,
    });
    assert.containsOnce($(".o_field_phone"), ".o_field_phone_sms");
});

QUnit.test("Sms button with option enable_sms set as False", async (assert) => {
    await makeView({
        type: "form",
        resModel: "visitor",
        resId: 1,
        serverData,
        mode: "readonly",
        arch: `
            <form>
                <sheet>
                    <field name="mobile" widget="phone" options="{'enable_sms': false}"/>
                </sheet>
            </form>`,
    });
    assert.containsNone($(".o_field_phone"), ".o_field_phone_sms");
});

QUnit.test("click on the sms button while creating a new record in a FormView", async (assert) => {
    const form = await makeView({
        type: "form",
        resModel: "partner",
        serverData,
        arch: `
            <form>
                <sheet>
                    <field name="foo"/>
                    <field name="mobile" widget="phone"/>
                </sheet>
            </form>`,
    });
    patchWithCleanup(form.env.services.action, {
        doAction: (action, options) => {
            assert.strictEqual(action.type, "ir.actions.act_window");
            assert.strictEqual(action.res_model, "sms.composer");
            options.onClose();
        },
    });
    await editInput(document.body, "[name='foo'] input", "John");
    await editInput(document.body, "[name='mobile'] input", "+32494444411");
    await click(document.body, ".o_field_phone_sms", { skipVisibilityCheck: true });
    assert.strictEqual($("[name='foo'] input").val(), "John");
    assert.strictEqual($("[name='mobile'] input").val(), "+32494444411");
});

QUnit.test(
    "click on the sms button in a FormViewDialog has no effect on the main form view",
    async (assert) => {
        serverData.models.partner.fields.partner_ids = {
            string: "one2many partners field",
            type: "one2many",
            relation: "partner",
        };
        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="foo"/>
                        <field name="mobile" widget="phone"/>
                        <field name="partner_ids">
                        <kanban>
                            <field name="display_name"/>
                            <templates>
                                <t t-name="kanban-box">
                                    <div><t t-esc="record.display_name"/></div>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                    </sheet>
                </form>`,
        });
        patchWithCleanup(form.env.services.action, {
            doAction: (action, options) => {
                assert.strictEqual(action.type, "ir.actions.act_window");
                assert.strictEqual(action.res_model, "sms.composer");
                options.onClose();
            },
        });
        await editInput(document.body, "[name='foo'] input", "John");
        await editInput(document.body, "[name='mobile'] input", "+32494444411");
        await click(document.body, "[name='partner_ids'] .o-kanban-button-new");
        assert.containsOnce(document.body, ".modal");

        await editInput($(".modal")[0], "[name='foo'] input", "Max");
        await editInput($(".modal")[0], "[name='mobile'] input", "+324955555");
        await click($(".modal")[0], ".o_field_phone_sms", { skipVisibilityCheck: true });
        assert.strictEqual($(".modal [name='foo'] input").val(), "Max");
        assert.strictEqual($(".modal [name='mobile'] input").val(), "+324955555");

        await click($(".modal")[0], ".o_form_button_cancel");
        assert.strictEqual($("[name='foo'] input").val(), "John");
        assert.strictEqual($("[name='mobile'] input").val(), "+32494444411");
    }
);
