// @ts-check

import { expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { CropOverlay } from "@web/components/barcode/crop_overlay";
import { browser } from "@web/core/browser/browser";

const STORAGE_KEY = "o-barcode-scanner-overlay";

/** @param {{ onResize?: Function }} [hooks] */
function makeHost({ onResize = () => {} } = {}) {
    class Host extends Component {
        static props = ["*"];
        static components = { CropOverlay };
        /** @type {{ isReady: boolean, tick: number }} */
        state;
        static template = xml`
            <div style="width: 300px; height: 200px;">
                <CropOverlay isReady="this.state.isReady" onResize.bind="this.onResize">
                    <div style="width: 300px; height: 200px;">video</div>
                </CropOverlay>
            </div>
            <span class="tick" t-out="this.state.tick"/>
        `;
        setup() {
            this.state = useState({ isReady: true, tick: 0 });
        }
        onResize(/** @type {any} */ area) {
            onResize(area);
        }
    }
    return Host;
}

function countStorageWrites() {
    const counter = { writes: 0 };
    patchWithCleanup(browser.localStorage, {
        setItem(key, value) {
            if (key === STORAGE_KEY) {
                counter.writes++;
            }
            return super.setItem(key, value);
        },
    });
    return counter;
}

test("unrelated re-renders do not persist or re-notify the crop area", async () => {
    const storage = countStorageWrites();
    let resizes = 0;
    const host = await mountWithCleanup(makeHost({ onResize: () => resizes++ }));
    await animationFrame();

    const afterMount = { writes: storage.writes, resizes };
    for (let i = 0; i < 3; i++) {
        host.state.tick++;
        await animationFrame();
    }

    expect(storage.writes - afterMount.writes).toBe(0);
    expect(resizes - afterMount.resizes).toBe(0);
});

test("the crop area is published once, and not republished unchanged", async () => {
    /** @type {any[]} */
    const areas = [];
    const host = await mountWithCleanup(
        makeHost({ onResize: (/** @type {any} */ area) => areas.push(area) }),
    );
    await animationFrame();

    expect(areas.length).toBe(1);
    expect(Object.keys(areas[0]).toSorted()).toEqual(["height", "width", "x", "y"]);

    host.state.isReady = false;
    await animationFrame();
    host.state.isReady = true;
    await animationFrame();
    expect(areas.length).toBe(1);
});

test("a drag persists the position exactly once, on pointer up", async () => {
    const storage = countStorageWrites();
    await mountWithCleanup(makeHost());
    await animationFrame();
    expect(storage.writes).toBe(0);

    const icon = queryOne(".o_crop_icon");
    const container = queryOne(".o_crop_container");
    icon.dispatchEvent(
        new PointerEvent("pointerdown", { bubbles: true, pointerId: 1 }),
    );
    for (const clientX of [120, 140, 160]) {
        container.dispatchEvent(
            new PointerEvent("pointermove", { bubbles: true, clientX, clientY: 80 }),
        );
    }
    expect(storage.writes).toBe(0);

    container.dispatchEvent(new PointerEvent("pointerup", { bubbles: true }));
    expect(storage.writes).toBe(1);

    container.dispatchEvent(new PointerEvent("pointerup", { bubbles: true }));
    expect(storage.writes).toBe(1);
});

test("the handle comes back where it was left, not on the opposite corner", async () => {
    const host = await mountWithCleanup(makeHost());
    await animationFrame();

    const icon = queryOne(".o_crop_icon");
    const container = queryOne(".o_crop_container");
    icon.dispatchEvent(
        new PointerEvent("pointerdown", { bubbles: true, pointerId: 1 }),
    );
    container.dispatchEvent(
        new PointerEvent("pointermove", { bubbles: true, clientX: 260, clientY: 170 }),
    );
    container.dispatchEvent(new PointerEvent("pointerup", { bubbles: true }));
    await animationFrame();

    const read = () => {
        const style = queryOne(".o_crop_container").style;
        return {
            crop: `${style.getPropertyValue("--o-crop-x")},${style.getPropertyValue("--o-crop-y")}`,
            icon: `${style.getPropertyValue("--o-crop-icon-x")},${style.getPropertyValue("--o-crop-icon-y")}`,
        };
    };
    const dragged = read();
    expect(dragged.crop).toBe("40px,30px");
    expect(dragged.icon).toBe("260px,170px");

    host.state.isReady = false;
    await animationFrame();
    host.state.isReady = true;
    await animationFrame();

    expect(read()).toEqual(dragged);
});
