/** @odoo-module **/

import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

import { Slider } from "@odx_owl/components/slider/slider";

test("rtl slider reverses horizontal keyboard movement and enforces minimum thumb spacing", async () => {
    class Parent extends Component {
        static components = { Slider };
        static template = xml`
            <Slider
                defaultValue="[20, 40]"
                dir="'rtl'"
                max="100"
                min="0"
                minStepsBetweenThumbs="2"
                name="'range'"
                step="10"
            />
        `;
    }

    await mountWithCleanup(Parent);

    expect(`.odx-slider__thumb`).toHaveCount(2);
    expect(document.querySelectorAll(`input[type="hidden"][name^="range"]`)[0]?.value).toBe("20");
    expect(document.querySelectorAll(`input[type="hidden"][name^="range"]`)[1]?.value).toBe("40");

    const secondThumb = document.querySelectorAll(`.odx-slider__thumb`)[1];
    secondThumb?.focus();
    await animationFrame();
    secondThumb?.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "ArrowLeft" }));
    await animationFrame();

    expect(document.querySelectorAll(`.odx-slider__thumb`)[1]?.getAttribute("aria-valuenow")).toBe("50");
    expect(document.querySelectorAll(`input[type="hidden"][name^="range"]`)[1]?.value).toBe("50");

    secondThumb?.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "ArrowRight" }));
    await animationFrame();
    secondThumb?.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "ArrowRight" }));
    await animationFrame();

    expect(document.querySelectorAll(`.odx-slider__thumb`)[1]?.getAttribute("aria-valuenow")).toBe("40");
    expect(document.querySelectorAll(`input[type="hidden"][name^="range"]`)[1]?.value).toBe("40");
});
