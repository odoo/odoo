import { expect, test } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { useService } from "@web/core/utils/hooks";

import { definePosModels } from "../data/generate_model_definitions.js";
import { setupPosEnv } from "../utils.js";

definePosModels();

const mountHolder = async (config = {}) => {
    class Dummy extends Component {
        static template = xml`<div/>`;
        static props = {};
        setup() {
            this.numberBuffer = useService("number_buffer");
            this.numberBuffer.use(config);
        }
    }
    const comp = await mountWithCleanup(Dummy, { props: {} });
    return comp;
};
const mountBufferHolder = async () => (await mountHolder()).numberBuffer;

test("digit entry, negation toggle and backspace", async () => {
    await setupPosEnv();
    const nb = await mountBufferHolder();
    nb._updateBuffer("1");
    nb._updateBuffer("2");
    expect(nb.get()).toBe("12");
    nb._updateBuffer("-");
    expect(nb.get()).toBe("-12");
    nb._updateBuffer("-");
    expect(nb.get()).toBe("12");
    nb._updateBuffer("+");
    expect(nb.get()).toBe("12");
    nb._updateBuffer("Backspace");
    expect(nb.get()).toBe("1");
});

test("negation as the first input yields -0", async () => {
    await setupPosEnv();
    const nb = await mountBufferHolder();
    nb._updateBuffer("-");
    expect(nb.get()).toBe("-0");
});

test("+N quick-cash keys add to the current value", async () => {
    await setupPosEnv();
    const nb = await mountBufferHolder();
    nb._updateBuffer("5");
    nb._updateBuffer("+10");
    expect(nb.getFloat()).toBe(15);
    nb._updateBuffer("+50");
    expect(nb.getFloat()).toBe(65);
});

test("the buffer stops growing past 12 digits", async () => {
    await setupPosEnv();
    const nb = await mountBufferHolder();
    for (let i = 0; i < 14; i++) {
        nb._updateBuffer("9");
    }
    expect(nb.get().length).toBeLessThan(14);
});

test("closing a holder cancels its keys before restoring the previous holder", async () => {
    await setupPosEnv();
    const parent = await mountHolder();
    const nb = parent.numberBuffer;
    nb.set("7");
    const popup = await mountHolder({
        triggerAtInput: () => expect.step("popup input"),
    });
    nb.sendKey("2");
    popup.__owl__.app.destroy();
    await advanceTime(100);
    expect(nb.get()).toBe("7");
    expect.verifySteps([]);
});

test("opening a popup applies the covered holder's pending keys to it", async () => {
    await setupPosEnv();
    const parent = await mountHolder({
        triggerAtInput: () => expect.step("parent input"),
    });
    const nb = parent.numberBuffer;
    nb.sendKey("2");
    const popup = await mountHolder({
        triggerAtInput: () => expect.step("popup input"),
    });
    await advanceTime(100);
    expect.verifySteps(["parent input"]);
    popup.__owl__.app.destroy();
    expect(nb.get()).toBe("2");
});

test("destroying the last holder cancels pending input callbacks", async () => {
    await setupPosEnv();
    const holder = await mountHolder({ triggerAtInput: () => expect.step("input") });
    holder.numberBuffer.sendKey("2");
    holder.__owl__.app.destroy();
    await advanceTime(100);
    holder.numberBuffer.sendKey("3");
    await advanceTime(100);
    expect.verifySteps([]);
});

test("keyboard and numpad events share a batch without losing either key", async () => {
    await setupPosEnv();
    const nb = await mountBufferHolder();
    window.dispatchEvent(new KeyboardEvent("keyup", { key: "1" }));
    nb.sendKey("2");
    nb.capture();
    expect(nb.get()).toBe("12");
});

test("positive sign after deleting an empty buffer does not throw", async () => {
    await setupPosEnv();
    const nb = await mountBufferHolder();
    nb.sendKey("Delete");
    nb.capture();
    expect(nb.get()).toBe(null);
    nb.sendKey("+");
    nb.capture();
    expect(nb.get()).toBe(null);
});

test("the browser Escape key invokes the configured escape action", async () => {
    await setupPosEnv();
    const holder = await mountHolder({ triggerAtEsc: () => expect.step("escape") });
    window.dispatchEvent(new KeyboardEvent("keyup", { key: "Escape" }));
    holder.numberBuffer.capture();
    expect.verifySteps(["escape"]);
});

test("a callback that closes its holder stops the remaining batch", async () => {
    await setupPosEnv();
    const parent = await mountHolder();
    const nb = parent.numberBuffer;
    nb.set("7");
    const popup = await mountHolder({
        triggerAtEnter: () => popup.__owl__.app.destroy(),
    });
    nb.sendKey("Enter");
    nb.sendKey("2");
    nb.capture();
    expect(nb.get()).toBe("7");
});

test("destroying an inactive holder preserves the active holder's pending keys", async () => {
    await setupPosEnv();
    const parent = await mountHolder();
    const popup = await mountHolder();
    const nb = popup.numberBuffer;
    nb.sendKey("2");
    parent.__owl__.app.destroy();
    nb.capture();
    expect(nb.get()).toBe("2");
});

test("a popup does not consume the previous holder's reset state", async () => {
    await setupPosEnv();
    const parent = await mountHolder();
    const nb = parent.numberBuffer;
    nb.reset();
    const popup = await mountHolder();
    nb.sendKey("2");
    nb.capture();
    popup.__owl__.app.destroy();
    nb.sendKey("Delete");
    nb.capture();
    expect(nb.get()).toBe("");
});

test("a buffer-update listener can destroy the last holder during input", async () => {
    await setupPosEnv();
    const holder = await mountHolder({
        triggerAtInput: () => expect.step("dead callback"),
    });
    const nb = holder.numberBuffer;
    nb.addEventListener("buffer-update", () => holder.__owl__.app.destroy(), {
        once: true,
    });
    nb.sendKey("2");
    nb.capture();
    expect.verifySteps([]);
});

test("buffer-update cannot redirect an input callback to the restored holder", async () => {
    await setupPosEnv();
    const parent = await mountHolder({
        triggerAtInput: () => expect.step("parent callback"),
    });
    const popup = await mountHolder({
        triggerAtInput: () => expect.step("dead callback"),
    });
    const nb = parent.numberBuffer;
    nb.addEventListener("buffer-update", () => popup.__owl__.app.destroy(), {
        once: true,
    });
    nb.sendKey("2");
    nb.capture();
    expect.verifySteps([]);
});
