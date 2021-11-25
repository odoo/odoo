/** @odoo-module **/

import { dialogService } from "@web/core/dialog/dialog_service";
import { registry } from "@web/core/registry";
import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";
import { makeFakeUserService } from "../helpers/mock_services";
import { click, triggerEvent } from "../helpers/utils";
import {
    setupControlPanelFavoriteMenuRegistry,
    setupControlPanelServiceRegistry,
} from "../search/helpers";
import { makeView } from "../views/helpers";

const serviceRegistry = registry.category("services");

let serverData;

function hasGroup(group) {
    return group === "base.group_allow_export";
}

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        date: { string: "A date", type: "date", searchable: true },
                        datetime: { string: "A datetime", type: "datetime", searchable: true },
                        display_name: { string: "Displayed name", type: "char", searchable: true },
                        foo: {
                            string: "Foo",
                            type: "char",
                            default: "My little Foo Value",
                            searchable: true,
                            trim: true,
                        },
                        bar: { string: "Bar", type: "boolean", default: true, searchable: true },
                        empty_string: {
                            string: "Empty string",
                            type: "char",
                            default: false,
                            searchable: true,
                            trim: true,
                        },
                        txt: {
                            string: "txt",
                            type: "text",
                            default: "My little txt Value\nHo-ho-hoooo Merry Christmas",
                        },
                        int_field: {
                            string: "int_field",
                            type: "integer",
                            sortable: true,
                            searchable: true,
                        },
                        qux: { string: "Qux", type: "float", digits: [16, 1], searchable: true },
                        p: {
                            string: "one2many field",
                            type: "one2many",
                            relation: "partner",
                            searchable: true,
                        },
                        trululu: {
                            string: "Trululu",
                            type: "many2one",
                            relation: "partner",
                            searchable: true,
                        },
                        timmy: {
                            string: "pokemon",
                            type: "many2many",
                            relation: "partner_type",
                            searchable: true,
                        },
                        product_id: {
                            string: "Product",
                            type: "many2one",
                            relation: "product",
                            searchable: true,
                        },
                        sequence: { type: "integer", string: "Sequence", searchable: true },
                        currency_id: {
                            string: "Currency",
                            type: "many2one",
                            relation: "currency",
                            searchable: true,
                        },
                        selection: {
                            string: "Selection",
                            type: "selection",
                            searchable: true,
                            selection: [
                                ["normal", "Normal"],
                                ["blocked", "Blocked"],
                                ["done", "Done"],
                            ],
                        },
                        document: { string: "Binary", type: "binary" },
                        hex_color: { string: "hexadecimal color", type: "char" },
                    },
                    records: [
                        {
                            id: 1,
                            date: "2017-02-03",
                            datetime: "2017-02-08 10:00:00",
                            display_name: "first record",
                            bar: true,
                            foo: "yop",
                            int_field: 10,
                            qux: 0.44444,
                            p: [],
                            timmy: [],
                            trululu: 4,
                            selection: "blocked",
                            document: "coucou==\n",
                            hex_color: "#ff0000",
                        },
                        {
                            id: 2,
                            display_name: "second record",
                            bar: true,
                            foo: "blip",
                            int_field: 0,
                            qux: 0,
                            p: [],
                            timmy: [],
                            trululu: 1,
                            sequence: 4,
                            currency_id: 2,
                            selection: "normal",
                        },
                        {
                            id: 4,
                            display_name: "aaa",
                            foo: "abc",
                            sequence: 9,
                            int_field: false,
                            qux: false,
                            selection: "done",
                        },
                        { id: 3, bar: true, foo: "gnap", int_field: 80, qux: -3.89859 },
                        { id: 5, bar: false, foo: "blop", int_field: -4, qux: 9.1, currency_id: 1 },
                    ],
                    onchanges: {},
                },
                product: {
                    fields: {
                        name: { string: "Product Name", type: "char", searchable: true },
                    },
                    records: [
                        {
                            id: 37,
                            display_name: "xphone",
                        },
                        {
                            id: 41,
                            display_name: "xpad",
                        },
                    ],
                },
                partner_type: {
                    fields: {
                        name: { string: "Partner Type", type: "char", searchable: true },
                        color: { string: "Color index", type: "integer", searchable: true },
                    },
                    records: [
                        { id: 12, display_name: "gold", color: 2 },
                        { id: 14, display_name: "silver", color: 5 },
                    ],
                },
                currency: {
                    fields: {
                        digits: { string: "Digits" },
                        symbol: { string: "Currency Sumbol", type: "char", searchable: true },
                        position: { string: "Currency Position", type: "char", searchable: true },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "$",
                            symbol: "$",
                            position: "before",
                        },
                        {
                            id: 2,
                            display_name: "€",
                            symbol: "€",
                            position: "after",
                        },
                    ],
                },
                "ir.translation": {
                    fields: {
                        lang: { type: "char" },
                        value: { type: "char" },
                        resId: { type: "integer" },
                    },
                    records: [
                        {
                            id: 99,
                            resId: 37,
                            value: "",
                            lang: "en_US",
                        },
                    ],
                },
            },
        };

        setupControlPanelFavoriteMenuRegistry();
        setupControlPanelServiceRegistry();
        serviceRegistry.add("dialog", dialogService);
        serviceRegistry.add("user", makeFakeUserService(hasGroup), { force: true });
    });

    QUnit.module("ProgressBarField");

    QUnit.test("ProgressBarField: max_value should update", async function (assert) {
        assert.expect(3);

        serverData.models.partner.records = serverData.models.partner.records.slice(0, 1);
        serverData.models.partner.records[0].qux = 2;

        serverData.models.partner.onchanges = {
            display_name(obj) {
                obj.int_field = 999;
                obj.qux = 5;
            },
        };

        const form = await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch:
                "<form>" +
                '<field name="display_name" />' +
                '<field name="qux" invisible="1" />' +
                "<field name=\"int_field\" widget=\"progressbar\" options=\"{'current_value': 'int_field', 'max_value': 'qux'}\" />" +
                "</form>",
            resId: 1,
            mockRPC(route, { method, args }) {
                if (method === "write") {
                    assert.deepEqual(
                        args[1],
                        { int_field: 999, qux: 5, display_name: "new name" },
                        "New value of progress bar saved"
                    );
                }
            },
        });

        assert.strictEqual(
            form.el.querySelector(".o_progressbar_value").innerText,
            "10 / 2",
            "The initial value of the progress bar should be correct"
        );
        // The view should be in edit mode
        await click(form.el.querySelector(".o_form_button_edit"));

        // trigger the onchange
        const field = form.el.querySelector(".o_input[name=display_name]");
        field.value = "new name";
        await triggerEvent(field, null, "change");
        await click(form.el.querySelector(".o_form_button_save"));

        assert.strictEqual(
            form.el.querySelector(".o_progressbar_value").innerText,
            "999 / 5",
            "The value of the progress bar should be correct after the update"
        );

        form.destroy();
    });

    QUnit.test(
        "ProgressBarField: value should update in edit mode when typing in input",
        async function (assert) {
            assert.expect(5);
            serverData.models.partner.records[0].int_field = 99;

            const form = await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch:
                    "<form>" +
                    '<field name="int_field" widget="progressbar" options="{\'editable\': true}" />' +
                    "</form>",
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

            // The view should be in edit mode by default
            await click(form.el.querySelector(".o_form_button_edit"));

            assert.ok(form.el.querySelector(".o_form_view .o_form_editable"), "Form in edit mode");

            const input = form.el.querySelector(".o_progressbar_value.o_input");

            assert.strictEqual(input.value, "99", "Initial value should be correct");

            // Clicking on the progress bar should not change the value
            await click(form.el.querySelector(".o_progress"));

            assert.strictEqual(input.value, "99", "Initial value in input is still correct");

            input.value = "69";
            await triggerEvent(input, null, "change");

            await click(form.el.querySelector(".o_form_button_save"));

            assert.strictEqual(
                form.el.querySelector(".o_progressbar_value").innerText,
                "69%",
                "New value should be different than initial after click"
            );
            form.destroy();
        }
    );

    QUnit.test(
        "ProgressBarField: value should update in edit mode when typing in input with field max value",
        async function (assert) {
            assert.expect(5);
            serverData.models.partner.records[0].int_field = 99;

            const form = await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch:
                    "<form>" +
                    '<field name="qux" invisible="1" />' +
                    "<field name=\"int_field\" widget=\"progressbar\" options=\"{'editable': true, 'max_value': 'qux'}\" />" +
                    "</form>",
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
            // The view should be in edit mode by default
            await click(form.el.querySelector(".o_form_button_edit"));

            assert.ok(form.el.querySelector(".o_form_view .o_form_editable"), "Form in edit mode");
            assert.ok(
                form.el.querySelector(".o_progressbar_value").value === "99" &&
                    form.el.querySelectorAll(".o_progressbar_value")[1].innerText === "0.44444",
                "Initial value should be correct"
            );

            await click(form.el.querySelector(".o_progress"));

            const input = form.el.querySelector(".o_progressbar_value.o_input");
            assert.strictEqual(input.value, "99", "Initial value in input is still correct");

            input.value = "69";
            await triggerEvent(input, null, "change");

            await click(form.el.querySelector(".o_form_button_save"));

            assert.strictEqual(
                form.el.querySelector(".o_progressbar_value").innerText,
                "69 / 0.44444",
                "New value should be different than initial after click"
            );

            form.destroy();
        }
    );

    QUnit.test(
        "ProgressBarField: max value should update in edit mode when typing in input with field max value",
        async function (assert) {
            assert.expect(5);
            serverData.models.partner.records[0].int_field = 99;

            const form = await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch:
                    "<form>" +
                    '<field name="qux" invisible="1" />' +
                    "<field name=\"int_field\" widget=\"progressbar\" options=\"{'editable': true, 'max_value': 'qux', 'edit_max_value': true}\" />" +
                    "</form>",
                resId: 1,
                mockRPC(route, { method, args }) {
                    if (method === "write") {
                        assert.strictEqual(args[1].qux, 69, "New value of progress bar saved");
                    }
                },
            });

            assert.strictEqual(
                form.el.querySelector(".o_progressbar_value").innerText,
                "99 / 0.44444",
                "Initial value should be correct"
            );
            // The view should be in edit mode by default
            await click(form.el.querySelector(".o_form_button_edit"));

            assert.ok(form.el.querySelector(".o_form_view .o_form_editable"), "Form in edit mode");

            await click(form.el.querySelector(".o_progress"));

            const input = form.el.querySelector(".o_progressbar_value.o_input");
            assert.strictEqual(input.value, "0.44444", "Initial value in input is correct");

            input.value = "69";
            await triggerEvent(input, null, "change");

            await click(form.el.querySelector(".o_form_button_save"));

            assert.strictEqual(
                form.el.querySelector(".o_progressbar_value").innerText,
                "99 / 69",
                "New value should be different than initial after click"
            );

            form.destroy();
        }
    );

    QUnit.test(
        "ProgressBarField: update both max value and current value in edit mode when both options are given",
        async function (assert) {
            assert.expect(7);
            serverData.models.partner.records[0].int_field = 99;

            const form = await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch:
                    "<form>" +
                    '<field name="qux" invisible="1" />' +
                    "<field name=\"int_field\" widget=\"progressbar\" options=\"{'editable': true, 'max_value': 'qux', 'edit_max_value': true, 'edit_current_value': true}\" />" +
                    "</form>",
                resId: 1,
                mockRPC(route, { method, args }) {
                    if (method === "write") {
                        assert.strictEqual(
                            args[1].int_field,
                            2000,
                            "New value of current value saved"
                        );
                        assert.strictEqual(args[1].qux, 69, "New value of max value saved");
                    }
                },
            });

            assert.strictEqual(
                form.el.querySelector(".o_progressbar_value").innerText,
                "99 / 0.44444",
                "Initial value should be correct"
            );
            // The view should be in edit mode by default
            await click(form.el.querySelector(".o_form_button_edit"));

            assert.ok(form.el.querySelector(".o_form_view .o_form_editable"), "Form in edit mode");

            await click(form.el.querySelector(".o_progress"));

            const currentVal = form.el.querySelectorAll(".o_progressbar_value.o_input")[0];
            const maxVal = form.el.querySelectorAll(".o_progressbar_value.o_input")[1];
            assert.strictEqual(currentVal.value, "99", "Initial value in input is correct");
            assert.strictEqual(maxVal.value, "0.44444", "Initial value in input is correct");

            currentVal.value = "2000";
            await triggerEvent(currentVal, null, "change");
            maxVal.value = "69";
            await triggerEvent(maxVal, null, "change");

            await click(form.el.querySelector(".o_form_button_save"));

            assert.strictEqual(
                form.el.querySelector(".o_progressbar_value").innerText,
                "2000 / 69",
                "New value should be different than initial after click"
            );

            form.destroy();
        }
    );

    QUnit.test("ProgressBarField: Standard readonly mode is readonly", async function (assert) {
        assert.expect(5);
        serverData.models.partner.records[0].int_field = 99;

        const form = await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch:
                "<form>" +
                '<field name="qux" invisible="1" />' +
                "<field name=\"int_field\" widget=\"progressbar\" options=\"{'editable': true, 'max_value': 'qux', 'edit_max_value': true}\" />" +
                "</form>",
            resId: 1,
            mockRPC(route) {
                assert.step(route);
            },
        });

        assert.ok(form.el.querySelector(".o_form_view .o_form_readonly"), "Form in readonly mode");

        assert.strictEqual(
            form.el.querySelector(".o_progressbar_value").innerText,
            "99 / 0.44444",
            "Initial value should be correct"
        );

        await click(form.el.querySelector(".o_progress"));

        assert.containsNone(form, ".o_progressbar_value.o_input", "no input in readonly mode");

        assert.verifySteps(["/web/dataset/call_kw/partner/read"]);

        form.destroy();
    });

    QUnit.skip(
        "ProgressBarField: write float instead of int works, in locale",
        async function (assert) {
            assert.expect(5);
            serverData.models.partner.records[0].int_field = 99;

            const form = await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch:
                    "<form>" +
                    '<field name="int_field" widget="progressbar" options="{\'editable\': true}" />' +
                    "</form>",
                resId: 1,
                translateParameters: {
                    thousands_sep: "#",
                    decimal_point: ":",
                },
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

            // The view should be in edit mode by default
            await click(form.el.querySelector(".o_form_button_edit"));

            assert.ok(form.el.querySelector(".o_form_view .o_form_editable"), "Form in edit mode");

            assert.strictEqual(
                form.el.querySelector(".o_progressbar_value").innerText,
                "99%",
                "Initial value should be correct"
            );

            await click(form.el.querySelector(".o_progress"));

            const input = form.el.querySelector(".o_progressbar_value.o_input");
            assert.strictEqual(input.value, "99", "Initial value in input is correct");

            await testUtils.fields.editAndTrigger(input, "1#037:9", ["input", "blur"]);

            await click(form.el.querySelector(".o_form_button_save"));

            assert.strictEqual(
                form.el.querySelector(".o_progressbar_value").innerText,
                "1k%",
                "New value should be different than initial after click"
            );

            form.destroy();
        }
    );

    QUnit.test(
        "ProgressBarField: write gibbrish instead of int throws warning",
        async function (assert) {
            assert.expect(6);

            serverData.models.partner.records[0].int_field = 99;
            const mock = () => {
                assert.step("Show error message");
                return () => {};
            };
            registry.category("services").add("notification", makeFakeNotificationService(mock), {
                force: true,
            });

            const form = await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch:
                    "<form>" +
                    '<field name="int_field" widget="progressbar" options="{\'editable\': true}" />' +
                    "</form>",
                resId: 1,
            });
            // The view should be in edit mode by default
            await click(form.el.querySelector(".o_form_button_edit"));

            assert.ok(form.el.querySelector(".o_form_view .o_form_editable"), "Form in edit mode");

            assert.strictEqual(
                form.el.querySelector(".o_progressbar_value").value,
                "99",
                "Initial value should be correct"
            );

            const input = form.el.querySelector(".o_progressbar_value.o_input");

            assert.strictEqual(input.value, "99", "Initial value in input is correct");

            input.value = "trente sept virgule neuf";
            await triggerEvent(input, null, "change");

            await click(form.el.querySelector(".o_form_button_save"));

            assert.strictEqual(
                form.el.querySelector(".o_progressbar_value").innerText,
                "99%",
                "The value has not changed"
            );
            assert.verifySteps(["Show error message"], "The error message was shown correctly");

            form.destroy();
        }
    );
});
