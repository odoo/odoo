// @ts-check

import { expect, test } from "@odoo/hoot";
import { manuallyDispatchProgrammaticEvent, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { CustomColorPicker } from "@web/components/color_picker/custom_color_picker/custom_color_picker";

test("entering a 6-digit hex preserves the current opacity", async () => {
    const picker = await mountWithCleanup(CustomColorPicker, {
        props: {
            defaultOpacity: 50,
        },
    });
    await animationFrame();

    const opacityBefore = picker.colorComponents.opacity;
    expect(opacityBefore).toBeLessThan(100);

    const hexInput = /** @type {HTMLInputElement} */ (queryOne("input.o_hex_input"));
    hexInput.value = "00FF00";
    hexInput.dispatchEvent(new InputEvent("input", { bubbles: true }));
    await animationFrame();

    expect(picker.colorComponents.red).toBe(0);
    expect(picker.colorComponents.green).toBe(255);
    expect(picker.colorComponents.blue).toBe(0);
    expect(picker.colorComponents.opacity).toBe(opacityBefore);
});

test("entering an 8-digit hex updates the opacity from its alpha channel", async () => {
    const picker = await mountWithCleanup(CustomColorPicker, {
        props: {
            defaultOpacity: 50,
        },
    });
    await animationFrame();

    expect(picker.colorComponents.opacity).toBeLessThan(100);

    const hexInput = /** @type {HTMLInputElement} */ (queryOne("input.o_hex_input"));
    hexInput.value = "00FF00FF";
    hexInput.dispatchEvent(new InputEvent("input", { bubbles: true }));
    await animationFrame();

    expect(picker.colorComponents.green).toBe(255);
    expect(picker.colorComponents.opacity).toBe(100);
});

test("a colour the parser cannot read still opens on something", async () => {
    const unparseable = [
        ["", ""],
        ["red", "red"],
        ["var(--o-color-1)", ""],
    ];
    for (const [index, [selectedColor, defaultColor]] of unparseable.entries()) {
        await mountWithCleanup(CustomColorPicker, {
            props: { selectedColor, defaultColor, onColorSelect: () => {} },
        });
        expect(".o_color_pick_area").toHaveCount(index + 1);
    }
});

test("arrows move the picker's two axes, control+ moves them finely", async () => {
    const picker = await mountWithCleanup(CustomColorPicker, {
        props: { selectedColor: "#BF4040", onColorSelect: () => {} },
    });
    await animationFrame();

    const press = (/** @type {string} */ key, /** @type {boolean} */ ctrl = false) =>
        queryOne("#picker_pointer").dispatchEvent(
            new KeyboardEvent("keydown", {
                key,
                ctrlKey: ctrl,
                bubbles: true,
                cancelable: true,
            }),
        );

    const before = { ...picker.colorComponents };
    press("ArrowUp");
    expect(picker.colorComponents.lightness).toBe(before.lightness + 10);
    expect(picker.colorComponents.saturation).toBe(before.saturation);

    press("ArrowLeft", true);
    expect(picker.colorComponents.saturation).toBe(before.saturation - 1);
    expect(picker.colorComponents.lightness).toBe(before.lightness + 10);

    press("ArrowRight");
    expect(picker.colorComponents.saturation).toBe(before.saturation - 1 + 10);

    for (let i = 0; i < 20; i++) {
        press("ArrowDown");
    }
    expect(picker.colorComponents.lightness).toBe(0);
});

test("the document hears pointer moves only while a drag is in progress", async () => {
    let moveListeners = 0;
    const { addEventListener, removeEventListener } = document;
    patchWithCleanup(document, {
        /** @type {typeof addEventListener} */
        addEventListener(type, listener, options) {
            if (type === "pointermove") {
                moveListeners++;
            }
            return addEventListener.call(this, type, listener, options);
        },
        /** @type {typeof removeEventListener} */
        removeEventListener(type, listener, options) {
            if (type === "pointermove") {
                moveListeners--;
            }
            return removeEventListener.call(this, type, listener, options);
        },
    });
    const picker = await mountWithCleanup(CustomColorPicker, {
        props: { selectedColor: "#BF4040", onColorSelect: () => {} },
    });
    await animationFrame();
    expect(moveListeners).toBe(0);

    const area = queryOne(".o_color_pick_area");
    const rect = area.getBoundingClientRect();
    const at = {
        clientX: rect.left + rect.width / 2,
        clientY: rect.top + rect.height / 2,
    };
    manuallyDispatchProgrammaticEvent(area, "pointerdown", at);
    expect(moveListeners).toBe(1);
    expect(picker.dragging).toBe("picker");

    manuallyDispatchProgrammaticEvent(area, "pointermove", {
        clientX: at.clientX,
        clientY: rect.top,
    });
    await animationFrame();
    expect(picker.colorComponents.lightness).toBe(100);

    manuallyDispatchProgrammaticEvent(area, "pointerup", at);
    expect(moveListeners).toBe(0);
    expect(picker.dragging).toBe(null);
});

test("a cancelled pointer stops color dragging without selecting a color", async () => {
    const picker = await mountWithCleanup(CustomColorPicker);
    const slider = picker.colorSliderRef.el;
    const { x, y } = slider.getBoundingClientRect();
    slider.dispatchEvent(
        new PointerEvent("pointerdown", {
            bubbles: true,
            pointerId: 41,
            clientX: x,
            clientY: y + 20,
        }),
    );
    document.dispatchEvent(new PointerEvent("pointercancel", { pointerId: 41 }));
    const color = picker.colorComponents.hex;
    document.dispatchEvent(
        new PointerEvent("pointermove", {
            pointerId: 41,
            clientX: x,
            clientY: y + 80,
        }),
    );
    await animationFrame();
    expect(picker.dragging).toBe(null);
    expect(picker.colorComponents.hex).toBe(color);
    expect(picker.shouldSetSelectedColor).toBe(false);
});

test("color dragging ignores secondary buttons and other pointers", async () => {
    const picker = await mountWithCleanup(CustomColorPicker);
    const slider = picker.colorSliderRef.el;
    const { x, y } = slider.getBoundingClientRect();
    slider.dispatchEvent(
        new PointerEvent("pointerdown", { bubbles: true, button: 2, pointerId: 3 }),
    );
    expect(picker.dragging).toBe(null);
    slider.dispatchEvent(
        new PointerEvent("pointerdown", {
            bubbles: true,
            pointerId: 3,
            clientX: x,
            clientY: y + 20,
        }),
    );
    const color = picker.colorComponents.hex;
    document.dispatchEvent(
        new PointerEvent("pointermove", { pointerId: 4, clientX: x, clientY: y + 90 }),
    );
    document.dispatchEvent(new PointerEvent("pointerup", { pointerId: 4 }));
    await animationFrame();
    expect(picker.colorComponents.hex).toBe(color);
    expect(picker.dragging).toBe("slider");
    document.dispatchEvent(new PointerEvent("pointerup", { pointerId: 3 }));
    expect(picker.dragging).toBe(null);
    expect(picker.shouldSetSelectedColor).toBe(true);
});

test("another pointer cannot replace the active pointer's queued move", async () => {
    const picker = await mountWithCleanup(CustomColorPicker);
    const slider = picker.colorSliderRef.el;
    const { x, y } = slider.getBoundingClientRect();
    slider.dispatchEvent(
        new PointerEvent("pointerdown", {
            bubbles: true,
            pointerId: 3,
            clientX: x,
            clientY: y + 20,
        }),
    );
    const move = (pointerId, offset) =>
        document.dispatchEvent(
            new PointerEvent("pointermove", {
                pointerId,
                clientX: x,
                clientY: y + offset,
            }),
        );
    move(3, 30);
    move(3, 60);
    move(4, 90);
    await animationFrame();
    expect(picker.colorComponents.hue).toBe(
        Math.round((360 * (slider.clientHeight - 60)) / slider.clientHeight),
    );
    document.dispatchEvent(new PointerEvent("pointercancel", { pointerId: 3 }));
});
