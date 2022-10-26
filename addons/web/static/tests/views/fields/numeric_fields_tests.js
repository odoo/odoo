/** @odoo-module **/

import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import { registry } from "@web/core/registry";
import { click, getFixture, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { localization } from "@web/core/l10n/localization";
import { useNumpadDecimal } from "@web/views/fields/numpad_decimal_hook";
import { makeTestEnv } from "../../helpers/mock_env";

const { Component, mount, useState, xml } = owl;

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
        patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: "." });
    });

    QUnit.module("Numeric fields");

    QUnit.test(
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
                    </form>`,
                resId: 1,
            });

            // Get all inputs
            const floatFactorField = target.querySelector(".o_field_float_factor input");
            const floatInput = target.querySelector(".o_field_float input");
            const integerInput = target.querySelector(".o_field_integer input");
            const monetaryInput = target.querySelector(".o_field_monetary input");
            const percentageInput = target.querySelector(".o_field_percentage input");

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

            await click(target.querySelector(".o_progress"));
            const progressbarInputs = target.querySelectorAll(".o_field_progressbar input");

            // After clicking the progressbar, focus is on the first input
            // and the value is highlighted. We get the length of each input value to
            // be able to set the cursor position at the end of the value.
            const [len1, len2] = [...progressbarInputs].map((input) => input.value.length);
            progressbarInputs[0].setSelectionRange(len1, len1);
            progressbarInputs[0].dispatchEvent(
                new KeyboardEvent("keydown", { code: "NumpadDecimal", key: "." })
            );
            progressbarInputs[0].dispatchEvent(
                new KeyboardEvent("keydown", { code: "NumpadDecimal", key: "," })
            );
            await nextTick();
            assert.strictEqual(progressbarInputs[0].value, "69🇧🇪🇧🇪");

            // Make sure that the cursor position is at the end of the value.
            progressbarInputs[1].setSelectionRange(len2, len2);
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

    QUnit.test(
        "Numeric fields: NumpadDecimal key is different from the decimalPoint",
        async function (assert) {
            await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch: /*xml*/ `
                    <form>
                        <field name="float_factor_field" options="{'factor': 0.5}"/>
                        <field name="qux"/>
                        <field name="int_field"/>
                        <field name="monetary"/>
                        <field name="currency_id" invisible="1"/>
                        <field name="percentage"/>
                        <field name="progressbar" widget="progressbar" options="{'editable': true, 'max_value': 'qux', 'edit_max_value': true, 'edit_current_value': true}"/>
                    </form>`,
                resId: 1,
            });

            // Get all inputs
            const floatFactorField = target.querySelector(".o_field_float_factor input");
            const floatInput = target.querySelector(".o_field_float input");
            const integerInput = target.querySelector(".o_field_integer input");
            const monetaryInput = target.querySelector(".o_field_monetary input");
            const percentageInput = target.querySelector(".o_field_percentage input");

            /**
             * Common assertion steps are extracted in this procedure.
             *
             * @param {object} params
             * @param {HTMLInputElement} params.el
             * @param {[number, number]} params.selectionRange
             * @param {string} params.expectedValue
             * @param {string} params.msg
             */
            async function testInputElementOnNumpadDecimal(params) {
                const { el, selectionRange, expectedValue, msg } = params;

                el.focus();
                el.setSelectionRange(...selectionRange);
                const numpadDecimalEvent = new KeyboardEvent("keydown", {
                    code: "NumpadDecimal",
                    key: ".",
                });
                numpadDecimalEvent.preventDefault = () => assert.step("preventDefault");
                el.dispatchEvent(numpadDecimalEvent);
                await nextTick();

                // dispatch an extra keydown event and assert that it's not default prevented
                const extraEvent = new KeyboardEvent("keydown", { code: "Digit1", key: "1" });
                extraEvent.preventDefault = () => {
                    throw new Error("should not be default prevented");
                };
                el.dispatchEvent(extraEvent);
                await nextTick();

                // Selection range should be at 1 + the specified selection start.
                assert.strictEqual(el.selectionStart, selectionRange[0] + 1);
                assert.strictEqual(el.selectionEnd, selectionRange[0] + 1);
                await nextTick();
                assert.verifySteps(
                    ["preventDefault"],
                    "NumpadDecimal event should be default prevented"
                );
                assert.strictEqual(el.value, expectedValue, msg);
            }

            await testInputElementOnNumpadDecimal({
                el: floatFactorField,
                selectionRange: [1, 3],
                expectedValue: "5,0",
                msg: "Float factor field from 5,00 to 5,0",
            });

            await testInputElementOnNumpadDecimal({
                el: floatInput,
                selectionRange: [0, 2],
                expectedValue: ",4",
                msg: "Float field from 0,4 to ,4",
            });

            await testInputElementOnNumpadDecimal({
                el: integerInput,
                selectionRange: [1, 2],
                expectedValue: "1,",
                msg: "Integer field from 10 to 1,",
            });

            await testInputElementOnNumpadDecimal({
                el: monetaryInput,
                selectionRange: [0, 3],
                expectedValue: ",9",
                msg: "Monetary field from 9,99 to ,9",
            });

            await testInputElementOnNumpadDecimal({
                el: percentageInput,
                selectionRange: [1, 1],
                expectedValue: "9,9",
                msg: "Percentage field from 99 to 9,9",
            });

            await click(target.querySelector(".o_progress"));
            const progressbarInputs = target.querySelectorAll(".o_field_progressbar input");

            await testInputElementOnNumpadDecimal({
                el: progressbarInputs[0],
                selectionRange: [2, 2],
                expectedValue: "69,",
                msg: "Progressbar field 1 from 69 to 69,",
            });

            await testInputElementOnNumpadDecimal({
                el: progressbarInputs[1],
                selectionRange: [1, 3],
                expectedValue: "0,4",
                msg: "Progressbar field 2 from 0,44 to 0,4",
            });
        }
    );

    QUnit.test(
        "useNumpadDecimal should synchronize handlers on input elements",
        async function (assert) {
            /**
             * Takes an array of input elements and asserts that each has the correct event listener.
             * @param {HTMLInputElement[]} inputEls
             */
            async function testInputElements(inputEls) {
                for (const inputEl of inputEls) {
                    inputEl.focus();
                    const numpadDecimalEvent = new KeyboardEvent("keydown", {
                        code: "NumpadDecimal",
                        key: ".",
                    });
                    numpadDecimalEvent.preventDefault = () => assert.step("preventDefault");
                    inputEl.dispatchEvent(numpadDecimalEvent);
                    await nextTick();

                    // dispatch an extra keydown event and assert that it's not default prevented
                    const extraEvent = new KeyboardEvent("keydown", { code: "Digit1", key: "1" });
                    extraEvent.preventDefault = () => {
                        throw new Error("should not be default prevented");
                    };
                    inputEl.dispatchEvent(extraEvent);
                    await nextTick();

                    assert.verifySteps(["preventDefault"]);
                }
            }

            class MyComponent extends Component {
                setup() {
                    useNumpadDecimal();
                    this.state = useState({ showOtherInput: false });
                }
            }
            MyComponent.template = xml`
                <main t-ref="numpadDecimal">
                    <input type="text" placeholder="input 1" />
                    <input t-if="state.showOtherInput" type="text" placeholder="input 2" />
                </main>
            `;
            const comp = await mount(MyComponent, target, { env: await makeTestEnv() });

            // Initially, only one input should be rendered.
            assert.containsOnce(target, "main > input");
            await testInputElements(target.querySelectorAll("main > input"));

            // We show the second input by manually updating the state.
            comp.state.showOtherInput = true;
            await nextTick();

            // The second input should also be able to handle numpad decimal.
            assert.containsN(target, "main > input", 2);
            await testInputElements(target.querySelectorAll("main > input"));
        }
    );
});
