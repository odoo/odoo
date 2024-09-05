import { beforeEach, expect, mountOnFixture, test } from "@odoo/hoot";
import { click, keyDown, pointerDown, queryAll, queryFirst } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    defineModels,
    defineParams,
    fields,
    models,
    mountView,
} from "@web/../tests/web_test_helpers";

import { Component, useState, xml } from "@odoo/owl";
import { useNumpadDecimal } from "@web/views/fields/numpad_decimal_hook";

class Partner extends models.Model {
    int_field = fields.Integer();
    qux = fields.Float({ digits: [16, 1] });
    currency_id = fields.Many2one({ relation: "currency" });
    float_factor_field = fields.Float();
    percentage = fields.Float();
    monetary = fields.Monetary({ currency_field: "" });
    progressbar = fields.Integer();

    _records = [
        {
            id: 1,
            int_field: 10,
            qux: 0.44444,
            float_factor_field: 9.99,
            percentage: 0.99,
            monetary: 9.99,
            currency_id: 1,
            progressbar: 69,
        },
    ];
}

class Currency extends models.Model {
    digits = fields.Float();
    symbol = fields.Char();
    position = fields.Char();

    _records = [{ id: 1, display_name: "$", symbol: "$", position: "before" }];
}

defineModels([Partner, Currency]);

beforeEach(() => {
    defineParams({ lang_parameters: { decimal_point: ",", thousands_sep: "." } });
});

test("Numeric fields: fields with keydown on numpad decimal key", async () => {
    defineParams({ lang_parameters: { decimal_point: "🇧🇪" } });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="float_factor_field" options="{'factor': 0.5}" widget="float_factor"/>
                <field name="qux"/>
                <field name="int_field"/>
                <field name="monetary"/>
                <field name="currency_id" invisible="1"/>
                <field name="percentage" widget="percentage"/>
                <field name="progressbar" widget="progressbar" options="{'editable': true, 'max_value': 'qux', 'edit_max_value': true}"/>
            </form>
        `,
        resId: 1,
    });

    // Dispatch numpad "dot" and numpad "comma" keydown events to all inputs and check
    // Numpad "comma" is specific to some countries (Brazil...)
    await click(".o_field_float_factor input");
    await keyDown("ArrowRight", { code: "ArrowRight" });
    await keyDown(".", { code: "NumpadDecimal" });
    await keyDown(",", { code: "NumpadDecimal" });
    await animationFrame();
    expect(".o_field_float_factor input").toHaveValue("5🇧🇪00🇧🇪🇧🇪");

    await click(".o_field_float input");
    await keyDown("ArrowRight", { code: "ArrowRight" });
    await keyDown(".", { code: "NumpadDecimal" });
    await keyDown(",", { code: "NumpadDecimal" });
    await animationFrame();
    expect(".o_field_float input").toHaveValue("0🇧🇪4🇧🇪🇧🇪");

    await click(".o_field_integer input");
    await keyDown("ArrowRight", { code: "ArrowRight" });
    await keyDown(".", { code: "NumpadDecimal" });
    await keyDown(",", { code: "NumpadDecimal" });
    await animationFrame();
    expect(".o_field_integer input").toHaveValue("10🇧🇪🇧🇪");

    await click(".o_field_monetary input");
    await keyDown("ArrowRight", { code: "ArrowRight" });
    await keyDown(".", { code: "NumpadDecimal" });
    await keyDown(",", { code: "NumpadDecimal" });
    await animationFrame();
    expect(".o_field_monetary input").toHaveValue("9🇧🇪99🇧🇪🇧🇪");

    await click(".o_field_percentage input");
    await keyDown("ArrowRight", { code: "ArrowRight" });
    await keyDown(".", { code: "NumpadDecimal" });
    await keyDown(",", { code: "NumpadDecimal" });
    await animationFrame();
    expect(".o_field_percentage input").toHaveValue("99🇧🇪🇧🇪");

    await click(".o_field_progressbar input");
    await animationFrame();

    await keyDown("ArrowRight", { code: "ArrowRight" });
    await keyDown(".", { code: "NumpadDecimal" });
    await keyDown(",", { code: "NumpadDecimal" });
    await animationFrame();
    expect(".o_field_progressbar input").toHaveValue("0🇧🇪44🇧🇪🇧🇪");
});

test("Numeric fields: NumpadDecimal key is different from the decimalPoint", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="float_factor_field" options="{'factor': 0.5}" widget="float_factor"/>
                <field name="qux"/>
                <field name="int_field"/>
                <field name="monetary"/>
                <field name="currency_id" invisible="1"/>
                <field name="percentage" widget="percentage"/>
                <field name="progressbar" widget="progressbar" options="{'editable': true, 'max_value': 'qux', 'edit_max_value': true}"/>
            </form>
        `,
        resId: 1,
    });

    // Get all inputs
    const floatFactorField = queryFirst(".o_field_float_factor input");
    const floatInput = queryFirst(".o_field_float input");
    const integerInput = queryFirst(".o_field_integer input");
    const monetaryInput = queryFirst(".o_field_monetary input");
    const percentageInput = queryFirst(".o_field_percentage input");
    const progressbarInput = queryFirst(".o_field_progressbar input");

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

        await pointerDown(el);
        await animationFrame();
        el.setSelectionRange(...selectionRange);
        const [event] = await keyDown(".", { code: "NumpadDecimal" });
        if (event.defaultPrevented) {
            expect.step("preventDefault");
        }
        await animationFrame();

        // dispatch an extra keydown event and expect that it's not default prevented
        const [extraEvent] = await keyDown("1", { code: "Digit1" });
        if (extraEvent.defaultPrevented) {
            throw new Error("should not be default prevented");
        }
        await animationFrame();

        // Selection range should be at +2 from the specified selection start (separator + character).
        expect(el.selectionStart).toBe(selectionRange[0] + 2);
        expect(el.selectionEnd).toBe(selectionRange[0] + 2);
        await animationFrame();
        // NumpadDecimal event should be default prevented
        expect.verifySteps(["preventDefault"]);
        expect(el).toHaveValue(expectedValue, { message: msg });
    }

    await testInputElementOnNumpadDecimal({
        el: floatFactorField,
        selectionRange: [1, 3],
        expectedValue: "5,10",
        msg: "Float factor field from 5,00 to 5,10",
    });

    await testInputElementOnNumpadDecimal({
        el: floatInput,
        selectionRange: [0, 2],
        expectedValue: ",14",
        msg: "Float field from 0,4 to ,14",
    });

    await testInputElementOnNumpadDecimal({
        el: integerInput,
        selectionRange: [1, 2],
        expectedValue: "1,1",
        msg: "Integer field from 10 to 1,1",
    });

    await testInputElementOnNumpadDecimal({
        el: monetaryInput,
        selectionRange: [0, 3],
        expectedValue: ",19",
        msg: "Monetary field from 9,99 to ,19",
    });

    await testInputElementOnNumpadDecimal({
        el: percentageInput,
        selectionRange: [1, 1],
        expectedValue: "9,19",
        msg: "Percentage field from 99 to 9,19",
    });

    await testInputElementOnNumpadDecimal({
        el: progressbarInput,
        selectionRange: [1, 3],
        expectedValue: "0,14",
        msg: "Progressbar field 2 from 0,44 to 0,14",
    });
});

test("useNumpadDecimal should synchronize handlers on input elements", async () => {
    /**
     * Takes an array of input elements and asserts that each has the correct event listener.
     * @param {HTMLInputElement[]} inputEls
     */
    async function testInputElements(inputEls) {
        for (const inputEl of inputEls) {
            await pointerDown(inputEl);
            await animationFrame();
            const [event] = await keyDown(".", { code: "NumpadDecimal" });
            if (event.defaultPrevented) {
                expect.step("preventDefault");
            }
            await animationFrame();

            // dispatch an extra keydown event and expect that it's not default prevented
            const [extraEvent] = await keyDown("1", { code: "Digit1" });
            if (extraEvent.defaultPrevented) {
                throw new Error("should not be default prevented");
            }
            await animationFrame();

            expect.verifySteps(["preventDefault"]);
        }
    }

    class MyComponent extends Component {
        static template = xml`
            <main t-ref="numpadDecimal">
                <input type="text" placeholder="input 1" />
                <input t-if="state.showOtherInput" type="text" placeholder="input 2" />
            </main>
        `;
        static props = ["*"];
        setup() {
            useNumpadDecimal();
            this.state = useState({ showOtherInput: false });
        }
    }

    const comp = await mountOnFixture(MyComponent);
    await animationFrame();

    // Initially, only one input should be rendered.
    expect("main > input").toHaveCount(1);
    await testInputElements(queryAll("main > input"));

    // We show the second input by manually updating the state.
    comp.state.showOtherInput = true;
    await animationFrame();

    // The second input should also be able to handle numpad decimal.
    expect("main > input").toHaveCount(2);
    await testInputElements(queryAll("main > input"));
});

test("select all content on focus", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `<form><field name="monetary"/></form>`,
    });

    const input = queryFirst(".o_field_widget[name='monetary'] input");
    await pointerDown(input);
    await animationFrame();
    expect(input.selectionStart).toBe(0);
    expect(input.selectionEnd).toBe(4);
});
