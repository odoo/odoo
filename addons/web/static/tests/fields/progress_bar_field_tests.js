/** @odoo-module **/

import { dialogService } from "@web/core/dialog/dialog_service";
import { registry } from "@web/core/registry";
import { makeFakeLocalizationService, makeFakeUserService } from "../helpers/mock_services";
import { click, makeDeferred, nextTick, triggerEvent, triggerEvents } from "../helpers/utils";
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
                        res_id: { type: "integer" },
                    },
                    records: [
                        {
                            id: 99,
                            res_id: 37,
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

    QUnit.skip("ProgressBarField: max_value should update", async function (assert) {
        assert.expect(3);

        this.data.partner.records = this.data.partner.records.slice(0, 1);
        this.data.partner.records[0].qux = 2;

        this.data.partner.onchanges = {
            display_name: function (obj) {
                obj.int_field = 999;
                obj.qux = 5;
            },
        };

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                "<form>" +
                '<field name="display_name" />' +
                '<field name="qux" invisible="1" />' +
                "<field name=\"int_field\" widget=\"progressbar\" options=\"{'current_value': 'int_field', 'max_value': 'qux'}\" />" +
                "</form>",
            res_id: 1,
            viewOptions: {
                mode: "edit",
            },
            mockRPC: function (route, args) {
                if (args.method === "write") {
                    assert.deepEqual(
                        args.args[1],
                        { int_field: 999, qux: 5, display_name: "new name" },
                        "New value of progress bar saved"
                    );
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(
            form.$(".o_progressbar_value").text(),
            "10 / 2",
            "The initial value of the progress bar should be correct"
        );

        // trigger the onchange
        await testUtils.fields.editInput(form.$(".o_input[name=display_name]"), "new name");

        assert.strictEqual(
            form.$(".o_progressbar_value").text(),
            "999 / 5",
            "The value of the progress bar should be correct after the update"
        );

        await testUtilsDom.click(form.$buttons.find(".o_form_button_save"));

        form.destroy();
    });

    QUnit.skip(
        "ProgressBarField: value should not update in readonly mode when sliding the bar",
        async function (assert) {
            assert.expect(4);
            this.data.partner.records[0].int_field = 99;

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    "<form>" +
                    '<field name="int_field" widget="progressbar" options="{\'editable\': true}" />' +
                    "</form>",
                res_id: 1,
                mockRPC: function (route, args) {
                    assert.step(route);
                    return this._super.apply(this, arguments);
                },
            });
            var $view = $("#qunit-fixture").contents();
            $view.prependTo("body"); // => select with click position

            assert.strictEqual(
                form.$(".o_progressbar_value").text(),
                "99%",
                "Initial value should be correct"
            );

            var $progressBarEl = form.$(".o_progress");
            var top = $progressBarEl.offset().top + 5;
            var left = $progressBarEl.offset().left + 5;
            try {
                testUtils.dom.triggerPositionalMouseEvent(left, top, "click");
            } catch (e) {
                form.destroy();
                $view.remove();
                throw new Error(
                    "The test fails to simulate a click in the screen. Your screen is probably too small or your dev tools is open."
                );
            }
            assert.strictEqual(
                form.$(".o_progressbar_value").text(),
                "99%",
                "New value should be different than initial after click"
            );

            assert.verifySteps(["/web/dataset/call_kw/partner/read"]);

            form.destroy();
            $view.remove();
        }
    );

    QUnit.skip(
        "ProgressBarField: value should not update in edit mode when sliding the bar",
        async function (assert) {
            assert.expect(6);
            this.data.partner.records[0].int_field = 99;

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    "<form>" +
                    '<field name="int_field" widget="progressbar" options="{\'editable\': true}" />' +
                    "</form>",
                res_id: 1,
                viewOptions: {
                    mode: "edit",
                },
                mockRPC: function (route, args) {
                    assert.step(route);
                    return this._super.apply(this, arguments);
                },
            });
            var $view = $("#qunit-fixture").contents();
            $view.prependTo("body"); // => select with click position

            assert.ok(form.$(".o_form_view").hasClass("o_form_editable"), "Form in edit mode");

            assert.strictEqual(
                form.$(".o_progressbar_value").text(),
                "99%",
                "Initial value should be correct"
            );

            var $progressBarEl = form.$(".o_progress");
            var top = $progressBarEl.offset().top + 5;
            var left = $progressBarEl.offset().left + 5;
            try {
                testUtils.dom.triggerPositionalMouseEvent(left, top, "click");
            } catch (e) {
                form.destroy();
                $view.remove();
                throw new Error(
                    "The test fails to simulate a click in the screen. Your screen is probably too small or your dev tools is open."
                );
            }
            assert.strictEqual(
                form.$(".o_progressbar_value.o_input").val(),
                "99",
                "Value of input is not changed"
            );
            await testUtilsDom.click(form.$buttons.find(".o_form_button_save"));

            assert.strictEqual(
                form.$(".o_progressbar_value").text(),
                "99%",
                "New value should be different than initial after click"
            );

            assert.verifySteps(["/web/dataset/call_kw/partner/read"]);

            form.destroy();
            $view.remove();
        }
    );

    QUnit.skip(
        "ProgressBarField: value should update in edit mode when typing in input",
        async function (assert) {
            assert.expect(5);
            this.data.partner.records[0].int_field = 99;

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    "<form>" +
                    '<field name="int_field" widget="progressbar" options="{\'editable\': true}" />' +
                    "</form>",
                res_id: 1,
                viewOptions: {
                    mode: "edit",
                },
                mockRPC: function (route, args) {
                    if (args.method === "write") {
                        assert.strictEqual(
                            args.args[1].int_field,
                            69,
                            "New value of progress bar saved"
                        );
                    }
                    return this._super.apply(this, arguments);
                },
            });

            assert.ok(form.$(".o_form_view").hasClass("o_form_editable"), "Form in edit mode");

            assert.strictEqual(
                form.$(".o_progressbar_value").text(),
                "99%",
                "Initial value should be correct"
            );

            await testUtilsDom.click(form.$(".o_progress"));

            var $valInput = form.$(".o_progressbar_value.o_input");
            assert.strictEqual($valInput.val(), "99", "Initial value in input is correct");

            await testUtils.fields.editAndTrigger($valInput, "69", ["input", "blur"]);

            await testUtilsDom.click(form.$buttons.find(".o_form_button_save"));

            assert.strictEqual(
                form.$(".o_progressbar_value").text(),
                "69%",
                "New value should be different than initial after click"
            );

            form.destroy();
        }
    );

    QUnit.skip(
        "ProgressBarField: value should update in edit mode when typing in input with field max value",
        async function (assert) {
            assert.expect(5);
            this.data.partner.records[0].int_field = 99;

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    "<form>" +
                    '<field name="qux" invisible="1" />' +
                    "<field name=\"int_field\" widget=\"progressbar\" options=\"{'editable': true, 'max_value': 'qux'}\" />" +
                    "</form>",
                res_id: 1,
                viewOptions: {
                    mode: "edit",
                },
                mockRPC: function (route, args) {
                    if (args.method === "write") {
                        assert.strictEqual(
                            args.args[1].int_field,
                            69,
                            "New value of progress bar saved"
                        );
                    }
                    return this._super.apply(this, arguments);
                },
            });

            assert.ok(form.$(".o_form_view").hasClass("o_form_editable"), "Form in edit mode");

            assert.strictEqual(
                form.$(".o_progressbar_value").text(),
                "99 / 0",
                "Initial value should be correct"
            );

            await testUtilsDom.click(form.$(".o_progress"));

            var $valInput = form.$(".o_progressbar_value.o_input");
            assert.strictEqual($valInput.val(), "99", "Initial value in input is correct");

            await testUtils.fields.editAndTrigger($valInput, "69", ["input", "blur"]);

            await testUtilsDom.click(form.$buttons.find(".o_form_button_save"));

            assert.strictEqual(
                form.$(".o_progressbar_value").text(),
                "69 / 0",
                "New value should be different than initial after click"
            );

            form.destroy();
        }
    );

    QUnit.skip(
        "ProgressBarField: max value should update in edit mode when typing in input with field max value",
        async function (assert) {
            assert.expect(5);
            this.data.partner.records[0].int_field = 99;

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    "<form>" +
                    '<field name="qux" invisible="1" />' +
                    "<field name=\"int_field\" widget=\"progressbar\" options=\"{'editable': true, 'max_value': 'qux', 'edit_max_value': true}\" />" +
                    "</form>",
                res_id: 1,
                viewOptions: {
                    mode: "edit",
                },
                mockRPC: function (route, args) {
                    if (args.method === "write") {
                        assert.strictEqual(args.args[1].qux, 69, "New value of progress bar saved");
                    }
                    return this._super.apply(this, arguments);
                },
            });

            assert.ok(form.$(".o_form_view").hasClass("o_form_editable"), "Form in edit mode");

            assert.strictEqual(
                form.$(".o_progressbar_value").text(),
                "99 / 0",
                "Initial value should be correct"
            );

            await testUtilsDom.click(form.$(".o_progress"));

            var $valInput = form.$(".o_progressbar_value.o_input");
            assert.strictEqual($valInput.val(), "0.44444", "Initial value in input is correct");

            await testUtils.fields.editAndTrigger($valInput, "69", ["input", "blur"]);

            await testUtilsDom.click(form.$buttons.find(".o_form_button_save"));

            assert.strictEqual(
                form.$(".o_progressbar_value").text(),
                "99 / 69",
                "New value should be different than initial after click"
            );

            form.destroy();
        }
    );

    QUnit.skip("ProgressBarField: Standard readonly mode is readonly", async function (assert) {
        assert.expect(5);
        this.data.partner.records[0].int_field = 99;

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                "<form>" +
                '<field name="qux" invisible="1" />' +
                "<field name=\"int_field\" widget=\"progressbar\" options=\"{'editable': true, 'max_value': 'qux', 'edit_max_value': true}\" />" +
                "</form>",
            res_id: 1,
            mockRPC: function (route, args) {
                assert.step(route);
                return this._super.apply(this, arguments);
            },
        });

        assert.ok(form.$(".o_form_view").hasClass("o_form_readonly"), "Form in readonly mode");

        assert.strictEqual(
            form.$(".o_progressbar_value").text(),
            "99 / 0",
            "Initial value should be correct"
        );

        await testUtilsDom.click(form.$(".o_progress"));

        assert.containsNone(form, ".o_progressbar_value.o_input", "no input in readonly mode");

        assert.verifySteps(["/web/dataset/call_kw/partner/read"]);

        form.destroy();
    });

    QUnit.skip(
        "ProgressBarField: max value should update in readonly mode with right parameter when typing in input with field max value",
        async function (assert) {
            assert.expect(5);
            this.data.partner.records[0].int_field = 99;

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    "<form>" +
                    '<field name="qux" invisible="1" />' +
                    "<field name=\"int_field\" widget=\"progressbar\" options=\"{'editable': true, 'max_value': 'qux', 'edit_max_value': true, 'editable_readonly': true}\" />" +
                    "</form>",
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.method === "write") {
                        assert.strictEqual(args.args[1].qux, 69, "New value of progress bar saved");
                    }
                    return this._super.apply(this, arguments);
                },
            });

            assert.ok(form.$(".o_form_view").hasClass("o_form_readonly"), "Form in readonly mode");

            assert.strictEqual(
                form.$(".o_progressbar_value").text(),
                "99 / 0",
                "Initial value should be correct"
            );

            await testUtilsDom.click(form.$(".o_progress"));

            var $valInput = form.$(".o_progressbar_value.o_input");
            assert.strictEqual($valInput.val(), "0.44444", "Initial value in input is correct");

            await testUtils.fields.editAndTrigger($valInput, "69", ["input", "blur"]);

            assert.strictEqual(
                form.$(".o_progressbar_value").text(),
                "99 / 69",
                "New value should be different than initial after changing it"
            );

            form.destroy();
        }
    );

    QUnit.skip(
        "ProgressBarField: value should update in readonly mode with right parameter when typing in input with field value",
        async function (assert) {
            assert.expect(5);
            this.data.partner.records[0].int_field = 99;

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    "<form>" +
                    '<field name="int_field" widget="progressbar" options="{\'editable\': true, \'editable_readonly\': true}" />' +
                    "</form>",
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.method === "write") {
                        assert.strictEqual(
                            args.args[1].int_field,
                            69,
                            "New value of progress bar saved"
                        );
                    }
                    return this._super.apply(this, arguments);
                },
            });

            assert.ok(form.$(".o_form_view").hasClass("o_form_readonly"), "Form in readonly mode");

            assert.strictEqual(
                form.$(".o_progressbar_value").text(),
                "99%",
                "Initial value should be correct"
            );

            await testUtilsDom.click(form.$(".o_progress"));

            var $valInput = form.$(".o_progressbar_value.o_input");
            assert.strictEqual($valInput.val(), "99", "Initial value in input is correct");

            await testUtils.fields.editAndTrigger($valInput, "69.6", ["input", "blur"]);

            assert.strictEqual(
                form.$(".o_progressbar_value").text(),
                "69%",
                "New value should be different than initial after changing it"
            );

            form.destroy();
        }
    );

    QUnit.skip(
        "ProgressBarField: write float instead of int works, in locale",
        async function (assert) {
            assert.expect(5);
            this.data.partner.records[0].int_field = 99;

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    "<form>" +
                    '<field name="int_field" widget="progressbar" options="{\'editable\': true}" />' +
                    "</form>",
                res_id: 1,
                viewOptions: {
                    mode: "edit",
                },
                translateParameters: {
                    thousands_sep: "#",
                    decimal_point: ":",
                },
                mockRPC: function (route, args) {
                    if (args.method === "write") {
                        assert.strictEqual(
                            args.args[1].int_field,
                            1037,
                            "New value of progress bar saved"
                        );
                    }
                    return this._super.apply(this, arguments);
                },
            });

            assert.ok(form.$(".o_form_view").hasClass("o_form_editable"), "Form in edit mode");

            assert.strictEqual(
                form.$(".o_progressbar_value").text(),
                "99%",
                "Initial value should be correct"
            );

            await testUtilsDom.click(form.$(".o_progress"));

            var $valInput = form.$(".o_progressbar_value.o_input");
            assert.strictEqual($valInput.val(), "99", "Initial value in input is correct");

            await testUtils.fields.editAndTrigger($valInput, "1#037:9", ["input", "blur"]);

            await testUtilsDom.click(form.$buttons.find(".o_form_button_save"));

            assert.strictEqual(
                form.$(".o_progressbar_value").text(),
                "1k%",
                "New value should be different than initial after click"
            );

            form.destroy();
        }
    );

    QUnit.skip(
        "ProgressBarField: write gibbrish instead of int throws warning",
        async function (assert) {
            assert.expect(5);
            this.data.partner.records[0].int_field = 99;

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    "<form>" +
                    '<field name="int_field" widget="progressbar" options="{\'editable\': true}" />' +
                    "</form>",
                res_id: 1,
                viewOptions: {
                    mode: "edit",
                },
                interceptsPropagate: {
                    call_service: function (ev) {
                        if (ev.data.service === "notification") {
                            assert.strictEqual(ev.data.method, "notify");
                            assert.strictEqual(
                                ev.data.args[0].message,
                                "Please enter a numerical value"
                            );
                        }
                    },
                },
            });

            assert.ok(form.$(".o_form_view").hasClass("o_form_editable"), "Form in edit mode");

            assert.strictEqual(
                form.$(".o_progressbar_value").text(),
                "99%",
                "Initial value should be correct"
            );

            await testUtilsDom.click(form.$(".o_progress"));

            var $valInput = form.$(".o_progressbar_value.o_input");
            assert.strictEqual($valInput.val(), "99", "Initial value in input is correct");

            await testUtils.fields.editAndTrigger($valInput, "trente sept virgule neuf", ["input"]);

            form.destroy();
        }
    );
});
