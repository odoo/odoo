/** @odoo-module **/

import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import { registry } from "@web/core/registry";
import { click, getFixture, nextTick } from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

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
                            sortable: true,
                            searchable: true,
                        },
                        qux: { string: "Qux", type: "float", digits: [16, 1], searchable: true },
                        currency_id: {
                            string: "Currency",
                            type: "many2one",
                            relation: "currency",
                            searchable: true,
                        },
                        float_factor_field: {
                            string: "Float Factor",
                            type: "float_factor",
                        },
                        percentage: {
                            string: "Percentage",
                            type: "percentage",
                        },
                        monetary: { string: "Monetary", type: "monetary" },
                        progressbar: {
                            type: "integer",
                        },
                        progressmax: {
                            type: "float",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            int_field: 10,
                            qux: 0.44444,
                            float_factor_field: 9.99,
                            percentage: 0.99,
                            monetary: 9.99,
                            currency_id: 1,
                            progressbar: 69,
                            progressmax: 5.41,
                        },
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
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("Numeric fields");

    QUnit.debug(
        "Numeric fields: fields with keydown on numpad decimal key",
        async function (assert) {
            registry.category("services").remove("localization");
            registry
                .category("services")
                .add("localization", makeFakeLocalizationService({ decimalPoint: "🇧🇪" }));
            await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch: `
                <form>
                    <field name="float_factor_field" options="{'factor': 0.5}"/>
                    <field name="qux"/>
                    <field name="int_field"/>
                    <field name="monetary"/>
                    <field name="currency_id" invisible="1"/>
                    <field name="percentage"/>
                    <field name="progressbar" widget="progressbar" options="{'editable': true, 'max_value': 'qux', 'edit_max_value': true, 'edit_current_value': true}"/>
                </form>
            `,
                resId: 1,
            });

            // Record edit mode
            await click(target.querySelector(".o_form_button_edit"));

            // Get all inputs
            const floatFactorField = target.querySelector(".o_field_float_factor input");
            const floatInput = target.querySelector(".o_field_float input");
            const integerInput = target.querySelector(".o_field_integer input");
            const monetaryInput = target.querySelector(".o_field_monetary input");
            const percentageInput = target.querySelector(".o_field_percentage input");
            const progressbarInputs = target.querySelectorAll(".o_field_progressbar input");

            // Dispatch numpad "dot" and numpad "comma" keydown events to all inputs and check
            // Numpad "comma" is specific to some countries (Brazil...)
            floatFactorField.dispatchEvent(
                new KeyboardEvent("keydown", { code: "NumpadDecimal", key: "." })
            );
            floatFactorField.dispatchEvent(
                new KeyboardEvent("keydown", { code: "NumpadDecimal", key: "," })
            );
            await nextTick();
            assert.strictEqual(floatFactorField.value, "5🇧🇪00🇧🇪🇧🇪");

            floatInput.dispatchEvent(
                new KeyboardEvent("keydown", { code: "NumpadDecimal", key: "." })
            );
            floatInput.dispatchEvent(
                new KeyboardEvent("keydown", { code: "NumpadDecimal", key: "," })
            );
            await nextTick();
            assert.strictEqual(floatInput.value, "0🇧🇪4🇧🇪🇧🇪");

            integerInput.dispatchEvent(
                new KeyboardEvent("keydown", { code: "NumpadDecimal", key: "." })
            );
            integerInput.dispatchEvent(
                new KeyboardEvent("keydown", { code: "NumpadDecimal", key: "," })
            );
            await nextTick();
            assert.strictEqual(integerInput.value, "10🇧🇪🇧🇪");

            monetaryInput.dispatchEvent(
                new KeyboardEvent("keydown", { code: "NumpadDecimal", key: "." })
            );
            monetaryInput.dispatchEvent(
                new KeyboardEvent("keydown", { code: "NumpadDecimal", key: "," })
            );
            await nextTick();
            assert.strictEqual(monetaryInput.value, "9🇧🇪99🇧🇪🇧🇪");

            percentageInput.dispatchEvent(
                new KeyboardEvent("keydown", { code: "NumpadDecimal", key: "." })
            );
            percentageInput.dispatchEvent(
                new KeyboardEvent("keydown", { code: "NumpadDecimal", key: "," })
            );
            await nextTick();
            assert.strictEqual(percentageInput.value, "99🇧🇪🇧🇪");

            progressbarInputs[0].dispatchEvent(
                new KeyboardEvent("keydown", { code: "NumpadDecimal", key: "." })
            );
            progressbarInputs[0].dispatchEvent(
                new KeyboardEvent("keydown", { code: "NumpadDecimal", key: "," })
            );
            await nextTick();
            assert.strictEqual(progressbarInputs[0].value, "69🇧🇪🇧🇪");

            progressbarInputs[1].dispatchEvent(
                new KeyboardEvent("keydown", { code: "NumpadDecimal", key: "." })
            );
            progressbarInputs[1].dispatchEvent(
                new KeyboardEvent("keydown", { code: "NumpadDecimal", key: "," })
            );
            await nextTick();
            assert.strictEqual(progressbarInputs[1].value, "0🇧🇪44🇧🇪🇧🇪");
        }
    );
});
