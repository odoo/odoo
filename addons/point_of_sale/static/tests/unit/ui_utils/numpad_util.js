import { animationFrame } from "@odoo/hoot-dom";
import { contains, getService } from "@web/../tests/web_test_helpers";
import { PosNumberBufferPlugin } from "@point_of_sale/app/plugins/pos_number_buffer_plugin";
import { ensurePane } from "./common";

const numpadButton = (label) => `.numpad button:text("${label}")`;

export async function clickNumpadButtons(...keys) {
    await ensurePane("left");
    const normalizedKeys = keys
        .flatMap((key) => {
            const value = key.toString();
            return /^-?\d*\.?\d+$/.test(value) ? value.split("") : [value];
        })
        .map((key) => (key === "-" ? "+/-" : key));

    for (const key of normalizedKeys) {
        await contains(numpadButton(key)).click();
        await animationFrame();
    }
}

export async function clickNumpad(key) {
    await ensurePane("left");
    const label = key === "backspace" ? "⌫" : key;
    await contains(numpadButton(label)).click();
    await animationFrame();
}

export async function enterNumpadValue(value) {
    for (const char of value.toString().split("")) {
        await clickNumpad(char);
    }
    getService(PosNumberBufferPlugin).capture(); // Prevents dropping more than 2 buffered keys
    await animationFrame();
}

export async function sendBufferKeys(...keys) {
    const numberBuffer = getService(PosNumberBufferPlugin);
    for (const key of keys.flat()) {
        numberBuffer.sendKey(key);
    }
    numberBuffer.capture();
    await animationFrame();
}
