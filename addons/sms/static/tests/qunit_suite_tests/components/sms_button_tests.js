/** @odoo-module **/

import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { click, editInput, getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";

let serverData;
let target;

QUnit.module(
    "fields",
    {
        beforeEach: function () {
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
                        records: [
                            {
                                id: 1,
                                mobile: "+32494444444",
                            },
                        ],
                    },
                },
            };
            setupViewRegistries();
            target = getFixture();
        },
    },
    function () {
        QUnit.module("SmsButton");

        QUnit.test("Sms button in form view", async function (assert) {
            await makeView({
                type: "form",
                resModel: "visitor",
                resId: 1,
                serverData,
                arch: /* xml */ `
                <form>
                    <sheet>
                        <field name="mobile" widget="phone"/>
                    </sheet>
                </form>`,
            });

            assert.containsOnce(
                target.querySelector(".o_field_phone"),
                ".o_field_phone_sms",
                "the button is present"
            );
        });

        QUnit.test("Sms button with option enable_sms set as False", async function (assert) {
            await makeView({
                type: "form",
                resModel: "visitor",
                resId: 1,
                serverData,
                mode: "readonly",
                arch: /* xml */ `
                <form>
                    <sheet>
                        <field name="mobile" widget="phone" options="{'enable_sms': false}"/>
                    </sheet>
                </form>`,
            });

            assert.containsNone(
                target.querySelector(".o_field_phone"),
                ".o_field_phone_sms",
                "the button is not present"
            );
        });

        QUnit.test(
            "click on the sms button while creating a new record in a FormView",
            async function (assert) {
                const form = await makeView({
                    type: "form",
                    resModel: "partner",
                    serverData,
                    arch: /* xml */ `
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
                await editInput(target, "[name='foo'] input", "John");
                await editInput(target, "[name='mobile'] input", "+32494444411");

                await click(target, ".o_field_phone_sms", true);
                assert.strictEqual(target.querySelector("[name='foo'] input").value, "John");
                assert.strictEqual(
                    target.querySelector("[name='mobile'] input").value,
                    "+32494444411"
                );
            }
        );

        QUnit.test(
            "click on the sms button in a FormViewDialog has no effect on the main form view",
            async function (assert) {
                serverData.models.partner.fields.partner_ids = {
                    string: "one2many partners field",
                    type: "one2many",
                    relation: "partner",
                };

                const form = await makeView({
                    type: "form",
                    resModel: "partner",
                    serverData,
                    arch: /* xml */ `
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
                await editInput(target, "[name='foo'] input", "John");
                await editInput(target, "[name='mobile'] input", "+32494444411");

                await click(target, "[name='partner_ids'] .o-kanban-button-new");
                assert.containsOnce(target, ".modal");

                const modal = target.querySelector(".modal");
                await editInput(modal, "[name='foo'] input", "Max");
                await editInput(modal, "[name='mobile'] input", "+324955555");

                await click(modal, ".o_field_phone_sms", true);
                assert.strictEqual(modal.querySelector("[name='foo'] input").value, "Max");
                assert.strictEqual(
                    modal.querySelector("[name='mobile'] input").value,
                    "+324955555"
                );

                await click(modal, ".o_form_button_cancel");
                assert.strictEqual(target.querySelector("[name='foo'] input").value, "John");
                assert.strictEqual(
                    target.querySelector("[name='mobile'] input").value,
                    "+32494444411"
                );
            }
        );
    }
);
