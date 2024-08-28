import { expect, mountOnFixture, test } from "@odoo/hoot";
import { getTemplate } from "@web/core/templates";
import { contains, getMockEnv } from "@web/../tests/web_test_helpers";
import { press } from "@odoo/hoot-dom";
import { enhancedButtons, Numpad } from "@point_of_sale/app/components/numpad/numpad";
import { buttonTriger } from "@point_of_sale/../tests/generic_helpers/numpad_util";
import { barcodeService } from "@barcodes/barcode_service";
import { localization } from "@web/core/l10n/localization";

const steps = [
    ["1", "1", "1"],
    ["2", "2", "12"],
    ["3", "3", "123"],
    ["⌫", "Backspace", "12"],
    [".", ".", "12."],
    ["1", "1", "12.1"],
    ["1", "1", "12.11"],
    ["⌫", "Backspace", "12.1"],
    ["⌫", "Backspace", "12."],
    ["3", "3", "12.3"],
    ["⌫", "Backspace", "12."],
    ["⌫", "Backspace", "12"],
    ["+/-", "-", "-12"],
    ["3", "3", "-123"],
    ["+/-", "-", "123"],
    ["+10", "+10", "133"],
    [".", ".", "133."],
    ["1", "1", "133.1"],
];

test("test mouse input", async () => {
    const config = {
        decimalPoint: ".",
        thousandsSep: ",",
        clicker: (key) => contains(buttonTriger(key)).click(),
    };
    await testKeys(
        [...steps, ["+10", "+10", "143.1"], ["+20", "+20", "163.1"], ["+50", "+50", "213.1"]],
        config
    );
});
test("test keyboard input", async () => {
    const config = {
        decimalPoint: ".",
        thousandsSep: ",",
        clicker: async (key) => {
            await press(key);
            await new Promise((resolve) =>
                setTimeout(resolve, barcodeService.maxTimeBetweenKeysInMs)
            );
        },
    };
    await testKeys(
        steps
            .map((items) => items.map((item) => item.replace("⌫", "Backspace")))
            .map((items) => items.map((item) => item.replace("+/-", "-"))),
        config
    );
});
test("test decimal point localization", async () => {
    const config = {
        decimalPoint: ",",
        thousandsSep: ".",
        clicker: (key) => contains(buttonTriger(key)).click(),
    };
    await testKeys(
        [...steps, ["+10", "+10", "143.1"], ["+20", "+20", "163.1"], ["+50", "+50", "213.1"]].map(
            (items) => [items[0].replace(".", ","), items[1], items[2]]
        ),
        config
    );
});

async function testKeys(steps, config) {
    let lastClick = {};
    Object.assign(localization, {
        decimalPoint: config.decimalPoint,
        thousandsSep: config.thousandsSep,
    });
    await mountOnFixture(Numpad, {
        props: {
            onClick: (a) => (lastClick = a),
            buttons: enhancedButtons(),
        },
        getTemplate,
        env: getMockEnv(),
        test: true,
    });

    let buffer = "";
    for (const [key, expectedLastKey, expectedBuffer] of steps) {
        await config.clicker(key);
        // debugger;
        expect(lastClick.key).toBe(expectedLastKey);
        buffer = lastClick.modifier(buffer);
        expect(buffer).toBe(expectedBuffer);
    }
}
