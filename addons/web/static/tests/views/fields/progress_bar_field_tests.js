/** @odoo-module **/

import {
    makeFakeLocalizationService,
    makeFakeNotificationService,
} from "@web/../tests/helpers/mock_services";
import {
    click,
    clickSave,
    editInput,
    getFixture,
    nextTick,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        int_field: {
                            string: "int_field",
                            type: "integer",
                        },
                        int_field2: {
                            string: "int_field",
                            type: "integer",
                        },
                        int_field3: {
                            string: "int_field",
                            type: "integer",
                        },
                        float_field: {
                            string: "Float_field",
                            type: "float",
                            digits: [16, 1],
                        },
                    },
                    records: [
                        {
                            int_field: 10,
                            float_field: 0.44444,
                        },
                    ],
                },
            },
        };

        setupViewRegistries();

        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });
    });

    QUnit.module("ProgressBarField");

    QUnit.test("ProgressBarField: max_value should update", async function (assert) {
        assert.expect(3);

        serverData.models.partner.records[0].float_field = 2;

        serverData.models.partner.onchanges = {
            display_name(obj) {
                obj.int_field = 999;
                obj.float_field = 5;
            },
        };

        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <field name="display_name" />
                    <field name="float_field" invisible="1" />
                    <field name="int_field" widget="progressbar" options="{'current_value': 'int_field', 'max_value': 'float_field'}" />
                </form>`,
            resId: 1,
            mockRPC(route, { method, args }) {
                if (method === "write") {
                    assert.deepEqual(
                        args[1],
                        { int_field: 999, float_field: 5, display_name: "new name" },
                        "New value of progress bar saved"
                    );
                }
            },
        });

        assert.strictEqual(
            target.querySelector(".o_progressbar").textContent,
            "10 / 2",
            "The initial value of the progress bar should be correct"
        );

        await editInput(target, ".o_field_widget[name=display_name] input", "new name");
        await clickSave(target);

        assert.strictEqual(
            target.querySelector(".o_progressbar").textContent,
            "999 / 5",
            "The value of the progress bar should be correct after the update"
        );
    });

    QUnit.test(
        "ProgressBarField: value should update in edit mode when typing in input",
        async function (assert) {
            assert.expect(4);
            serverData.models.partner.records[0].int_field = 99;

            await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch: `
                    <form>
                        <field name="int_field" widget="progressbar" options="{'editable': true}"/>
                    </form>`,
                resId: 1,
                mockRPC(route, { method, args }) {
                    if (method === "write") {
                        assert.strictEqual(
                            args[1].int_field,
                            69,
                            "New value of progress bar saved"
                        );
                    }
                },
            });

            assert.strictEqual(
                target.querySelector(".o_progressbar_value .o_input").value +
                    target.querySelector(".o_progressbar").textContent,
                "99%",
                "Initial value should be correct"
            );

            await editInput(target, ".o_progressbar_value .o_input", "69");
            await click(target, ".o_form_view");
            await nextTick();
            assert.strictEqual(
                target.querySelector(".o_progressbar_value .o_input").value,
                "69",
                "New value should be different after focusing out of the field"
            );

            await clickSave(target);
            assert.strictEqual(
                target.querySelector(".o_progressbar_value .o_input").value,
                "69",
                "New value is still displayed after save"
            );
        }
    );

    QUnit.test(
        "ProgressBarField: value should update in edit mode when typing in input with field max value",
        async function (assert) {
            assert.expect(4);
            serverData.models.partner.records[0].int_field = 99;

            await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch: `
                    <form>
                        <field name="float_field" invisible="1" />
                        <field name="int_field" widget="progressbar" options="{'editable': true, 'max_value': 'float_field'}" />
                    </form>`,
                resId: 1,
                mockRPC(route, { method, args }) {
                    if (method === "write") {
                        assert.strictEqual(
                            args[1].int_field,
                            69,
                            "New value of progress bar saved"
                        );
                    }
                },
            });

            assert.ok(target.querySelector(".o_form_view .o_form_editable"), "Form in edit mode");
            assert.strictEqual(
                target.querySelector(".o_progressbar_value .o_input").value +
                    target.querySelector(".o_progressbar").textContent,
                "99 / 0",
                "Initial value should be correct"
            );

            await editInput(target, ".o_progressbar_value .o_input", "69");
            await clickSave(target);

            assert.strictEqual(
                target.querySelector(".o_progressbar_value .o_input").value +
                    target.querySelector(".o_progressbar").textContent,
                "69 / 0",
                "New value should be different than initial after click"
            );
        }
    );

    QUnit.test(
        "ProgressBarField: max value should update in edit mode when typing in input with field max value",
        async function (assert) {
            assert.expect(5);
            serverData.models.partner.records[0].int_field = 99;

            await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch: `
                    <form>
                        <field name="float_field" invisible="1" />
                        <field name="int_field" widget="progressbar" options="{'editable': true, 'max_value': 'float_field', 'edit_max_value': true}" />
                    </form>`,
                resId: 1,
                mockRPC(route, { method, args }) {
                    if (method === "write") {
                        assert.strictEqual(
                            args[1].float_field,
                            69,
                            "New value of progress bar saved"
                        );
                    }
                },
            });

            assert.strictEqual(
                target.querySelector(".o_progressbar").textContent +
                    target.querySelector(".o_progressbar_value .o_input").value,
                "99 / 0",
                "Initial value should be correct"
            );
            assert.ok(target.querySelector(".o_form_view .o_form_editable"), "Form in edit mode");
            target.querySelector(".o_progressbar input").focus();

            await nextTick();
            assert.strictEqual(
                target.querySelector(".o_progressbar").textContent +
                    target.querySelector(".o_progressbar_value .o_input").value,
                "99 / 0.44",
                "Initial value is not formatted when focused"
            );

            await editInput(target, ".o_progressbar_value .o_input", "69");
            await clickSave(target);
            assert.strictEqual(
                target.querySelector(".o_progressbar").textContent +
                    target.querySelector(".o_progressbar_value .o_input").value,
                "99 / 69",
                "New value should be different than initial after click"
            );
        }
    );

    QUnit.test("ProgressBarField: Standard readonly mode is readonly", async function (assert) {
        serverData.models.partner.records[0].int_field = 99;

        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form edit="0">
                    <field name="float_field" invisible="1"/>
                    <field name="int_field" widget="progressbar" options="{'editable': true, 'max_value': 'float_field', 'edit_max_value': true}"/>
                </form>`,
            resId: 1,
            mockRPC(route) {
                assert.step(route);
            },
        });

        assert.strictEqual(
            target.querySelector(".o_progressbar").textContent,
            "99 / 0",
            "Initial value should be correct"
        );

        await click(target.querySelector(".o_progress"));

        assert.containsNone(target, ".o_progressbar_value .o_input", "no input in readonly mode");

        assert.verifySteps([
            "/web/dataset/call_kw/partner/get_views",
            "/web/dataset/call_kw/partner/read",
        ]);
    });

    QUnit.test("ProgressBarField: field is editable in kanban", async function (assert) {
        assert.expect(7);

        serverData.models.partner.fields.int_field.readonly = true;
        serverData.models.partner.records[0].int_field = 99;

        await makeView({
            serverData,
            type: "kanban",
            resModel: "partner",
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="int_field" title="ProgressBarTitle" widget="progressbar" options="{'editable': true, 'max_value': 'float_field'}" />
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            resId: 1,
            mockRPC(route, { method, args }) {
                if (method === "write") {
                    assert.strictEqual(args[1].int_field, 69, "New value of progress bar saved");
                }
            },
        });

        assert.strictEqual(
            target.querySelector(".o_progressbar_value .o_input").value,
            "99",
            "Initial input value should be correct"
        );
        assert.strictEqual(
            target.querySelector(".o_progressbar_value span").textContent,
            "100",
            "Initial max value should be correct"
        );
        assert.strictEqual(
            target.querySelector(".o_progressbar_title").textContent,
            "ProgressBarTitle"
        );

        await editInput(target, ".o_progressbar_value .o_input", "69");
        assert.strictEqual(
            target.querySelector(".o_progressbar_value .o_input").value,
            "69",
            "New input value should now be different"
        );
        assert.strictEqual(
            target.querySelector(".o_progressbar_value span").textContent,
            "100",
            "Max value is still the same be correct"
        );
        assert.strictEqual(
            target.querySelector(".o_progressbar_title").textContent,
            "ProgressBarTitle"
        );
    });

    QUnit.test("force readonly in kanban", async (assert) => {
        assert.expect(2);

        serverData.models.partner.records[0].int_field = 99;

        await makeView({
            serverData,
            type: "kanban",
            resModel: "partner",
            arch: /* xml */ `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="int_field" widget="progressbar" options="{'editable': true, 'max_value': 'float_field', 'readonly': True}" />
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            resId: 1,
            mockRPC(route, { method, args }) {
                if (method === "write") {
                    throw new Error("Not supposed to write");
                }
            },
        });

        assert.strictEqual(target.querySelector(".o_progressbar").textContent, "99 / 100");
        assert.containsNone(target, ".o_progressbar_value .o_input");
    });

    QUnit.test(
        "ProgressBarField: readonly and editable attrs/options in kanban",
        async function (assert) {
            assert.expect(4);
            serverData.models.partner.records[0].int_field = 29;
            serverData.models.partner.records[0].int_field2 = 59;
            serverData.models.partner.records[0].int_field3 = 99;

            await makeView({
                serverData,
                type: "kanban",
                resModel: "partner",
                arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="int_field" readonly="1" widget="progressbar" options="{'max_value': 'float_field'}" />
                                <field name="int_field2" widget="progressbar" options="{'max_value': 'float_field'}" />
                                <field name="int_field3" widget="progressbar" options="{'editable': true, 'max_value': 'float_field'}" />
                            </div>
                        </t>
                    </templates>
                </kanban>`,
                resId: 1,
            });

            assert.containsNone(
                target,
                "[name='int_field'] .o_progressbar_value .o_input",
                "the field is still in readonly since there is readonly attribute"
            );
            assert.containsNone(
                target,
                "[name='int_field2'] .o_progressbar_value .o_input",
                "the field is still in readonly since the editable option is missing"
            );
            assert.containsOnce(
                target,
                "[name='int_field3'] .o_progressbar_value .o_input",
                "the field is still in readonly since the editable option is missing"
            );

            await editInput(
                target,
                ".o_field_progressbar[name='int_field3'] .o_progressbar_value .o_input",
                "69"
            );
            assert.strictEqual(
                target.querySelector(
                    ".o_field_progressbar[name='int_field3'] .o_progressbar_value .o_input"
                ).value,
                "69",
                "New value should be different than initial after click"
            );
        }
    );

    QUnit.test(
        "ProgressBarField: write float instead of int works, in locale",
        async function (assert) {
            assert.expect(4);
            serverData.models.partner.records[0].int_field = 99;

            await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch: `
                    <form>
                        <field name="int_field" widget="progressbar" options="{'editable': true}"/>
                    </form>`,
                resId: 1,
                mockRPC: function (route, { method, args }) {
                    if (method === "write") {
                        assert.strictEqual(
                            args[1].int_field,
                            1037,
                            "New value of progress bar saved"
                        );
                    }
                },
            });

            registry.category("services").remove("localization");
            registry
                .category("services")
                .add(
                    "localization",
                    makeFakeLocalizationService({ thousandsSep: "#", decimalPoint: ":" })
                );

            assert.strictEqual(
                target.querySelector(".o_progressbar_value .o_input").value +
                    target.querySelector(".o_progressbar").textContent,
                "99%",
                "Initial value should be correct"
            );

            assert.ok(target.querySelector(".o_form_view .o_form_editable"), "Form in edit mode");

            await editInput(target, ".o_field_widget input", "1#037:9");
            await clickSave(target);

            assert.strictEqual(
                target.querySelector(".o_progressbar_value .o_input").value,
                "1k",
                "New value should be different than initial after click"
            );
        }
    );

    QUnit.test(
        "ProgressBarField: write gibbrish instead of int throws warning",
        async function (assert) {
            serverData.models.partner.records[0].int_field = 99;
            const mock = () => {
                assert.step("Show error message");
                return () => {};
            };
            registry.category("services").add("notification", makeFakeNotificationService(mock), {
                force: true,
            });

            await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch: `
                    <form>
                        <field name="int_field" widget="progressbar" options="{'editable': true}"/>
                    </form>`,
                resId: 1,
            });

            assert.strictEqual(
                target.querySelector(".o_progressbar_value .o_input").value,
                "99",
                "Initial value in input is correct"
            );

            await editInput(target, ".o_progressbar_value .o_input", "trente sept virgule neuf");
            await clickSave(target);
            assert.containsOnce(target, ".o_form_dirty", "The form has not been saved");
            assert.verifySteps(["Show error message"], "The error message was shown correctly");
        }
    );
});
