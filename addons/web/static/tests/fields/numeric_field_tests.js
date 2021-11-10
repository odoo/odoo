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

    QUnit.module("NumericField");

    QUnit.skip("NumericField: fields with keydown on numpad decimal key", async function (assert) {
        assert.expect(5);

        this.data.partner.fields.float_factor_field = {
            string: "Float Factor",
            type: "float_factor",
        };
        this.data.partner.records[0].float_factor_field = 9.99;

        this.data.partner.fields.monetary = { string: "Monetary", type: "monetary" };
        this.data.partner.records[0].monetary = 9.99;
        this.data.partner.records[0].currency_id = 1;

        this.data.partner.fields.percentage = { string: "Percentage", type: "percentage" };
        this.data.partner.records[0].percentage = 0.99;

        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: `
                <form string="Partners">
                    <field name="float_factor_field" options="{'factor': 0.5}"/>
                    <field name="qux"/>
                    <field name="int_field"/>
                    <field name="monetary"/>
                    <field name="currency_id" invisible="1"/>
                    <field name="percentage"/>
                </form>
            `,
            res_id: 1,
            translateParameters: {
                decimal_point: "🇧🇪",
            },
        });

        // Record edit mode
        await testUtilsDom.click(form.el.querySelector(".o_form_button_edit"));

        // Get all inputs
        const floatFactorField = form.el.querySelector('.o_input[name="float_factor_field"]');
        const floatInput = form.el.querySelector('.o_input[name="qux"]');
        const integerInput = form.el.querySelector('.o_input[name="int_field"]');
        const monetaryInput = form.el.querySelector('.o_input[name="monetary"]');
        const percentageInput = form.el.querySelector('.o_input[name="percentage"]');

        // Dispatch numpad "dot" and numpad "comma" keydown events to all inputs and check
        // Numpad "comma" is specific to some countries (Brazil...)
        floatFactorField.dispatchEvent(
            new KeyboardEvent("keydown", { code: "NumpadDecimal", key: "." })
        );
        floatFactorField.dispatchEvent(
            new KeyboardEvent("keydown", { code: "NumpadDecimal", key: "," })
        );
        await testUtils.nextTick();
        assert.ok(floatFactorField.value.endsWith("🇧🇪🇧🇪"));

        floatInput.dispatchEvent(new KeyboardEvent("keydown", { code: "NumpadDecimal", key: "." }));
        floatInput.dispatchEvent(new KeyboardEvent("keydown", { code: "NumpadDecimal", key: "," }));
        await testUtils.nextTick();
        assert.ok(floatInput.value.endsWith("🇧🇪🇧🇪"));

        integerInput.dispatchEvent(
            new KeyboardEvent("keydown", { code: "NumpadDecimal", key: "." })
        );
        integerInput.dispatchEvent(
            new KeyboardEvent("keydown", { code: "NumpadDecimal", key: "," })
        );
        await testUtils.nextTick();
        assert.ok(integerInput.value.endsWith("🇧🇪🇧🇪"));

        monetaryInput.dispatchEvent(
            new KeyboardEvent("keydown", { code: "NumpadDecimal", key: "." })
        );
        monetaryInput.dispatchEvent(
            new KeyboardEvent("keydown", { code: "NumpadDecimal", key: "," })
        );
        await testUtils.nextTick();
        assert.ok(monetaryInput.querySelector("input.o_input").value.endsWith("🇧🇪🇧🇪"));

        percentageInput.dispatchEvent(
            new KeyboardEvent("keydown", { code: "NumpadDecimal", key: "." })
        );
        percentageInput.dispatchEvent(
            new KeyboardEvent("keydown", { code: "NumpadDecimal", key: "," })
        );
        await testUtils.nextTick();
        assert.ok(percentageInput.querySelector("input.o_input").value.endsWith("🇧🇪🇧🇪"));

        form.destroy();
    });
});
