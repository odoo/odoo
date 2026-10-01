import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, hover, pointerDown, queryOne } from "@odoo/hoot-dom";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

import { compareImageXml, setupCompareImageTest } from "./helpers";

setupInteractionWhiteList("website.compare_image");

describe.current.tags("interaction_dev");

/**
 * The divider sits at the position being asserted, so a drag is always aimed at
 * the centre of the frame and measured from there: the interaction tracks the
 * distance covered since the press, not the pointer's place in the frame.
 */
function getFrameCentre() {
    const { left, top, width, height } = queryOne(".s_compare_image_frame").getBoundingClientRect();
    return { x: left + width / 2, y: top + height / 2 };
}

function getPosition() {
    return queryOne(".s_compare_image").style.getPropertyValue("--compare-pos");
}

/**
 * @param {{ x: number, y: number }} from the position the drag started at
 * @param {number} dx
 * @param {number} dy
 */
async function moveBy(from, dx, dy) {
    await hover(".s_compare_image_divider", { position: { x: from.x + dx, y: from.y + dy } });
    // The move handler is throttled for animation, so it only runs on the frame
    // following the event.
    await animationFrame();
}

test("the saved position is kept on start", async () => {
    setupCompareImageTest();
    const { core } = await startInteractions(compareImageXml());

    expect(core.interactions).toHaveLength(1);
    expect(getPosition()).toBe("50%");
});

test("dragging the divider moves it by the distance covered", async () => {
    setupCompareImageTest();
    await startInteractions(compareImageXml());

    const start = getFrameCentre();
    await pointerDown(".s_compare_image_divider", { position: start });
    // A quarter of the 400px frame.
    await moveBy(start, 100, 0);

    expect(getPosition()).toBe("75%");

    await moveBy(start, -100, 0);

    expect(getPosition()).toBe("25%");
});

test("the position is clamped to the frame", async () => {
    setupCompareImageTest();
    await startInteractions(compareImageXml());

    const start = getFrameCentre();
    await pointerDown(".s_compare_image_divider", { position: start });
    // Pointer capture keeps the events coming once the pointer is outside the
    // frame, so the raw ratio goes past both edges.
    await moveBy(start, 1000, 0);

    expect(getPosition()).toBe("100%");

    await moveBy(start, -1000, 0);

    expect(getPosition()).toBe("0%");
});

test("the horizontal variant tracks the vertical axis", async () => {
    setupCompareImageTest();
    await startInteractions(compareImageXml("s_compare_image_horizontal"));

    const start = getFrameCentre();
    await pointerDown(".s_compare_image_divider", { position: start });
    await moveBy(start, 100, 0);

    expect(getPosition()).toBe("50%");

    // A quarter of the 200px frame.
    await moveBy(start, 0, 50);

    expect(getPosition()).toBe("75%");
});

// test("a move without a press is ignored", async () => {
//     setupCompareImageTest();
//     await startInteractions(compareImageXml());

//     const start = getFrameCentre();
//     await moveBy(start, 100, 0);

//     expect(getPosition()).toBe("50%");
// });

// test("a non-primary button does not start a drag", async () => {
//     setupCompareImageTest();
//     await startInteractions(compareImageXml());

//     const start = getFrameCentre();
//     await pointerDown(".s_compare_image_divider", { position: start, button: 1 });
//     await moveBy(start, 100, 0);

//     expect(getPosition()).toBe("50%");
// });

// test("releasing applies the last position even if its frame never ran", async () => {
//     setupCompareImageTest();
//     await startInteractions(compareImageXml());

//     const start = getFrameCentre();
//     await pointerDown(".s_compare_image_divider", { position: start });
//     const end = { x: start.x + 100, y: start.y };
//     // No animation frame in between: the throttled handler still has one
//     // pending, which the release has to flush synchronously.
//     await hover(".s_compare_image_divider", { position: end });
//     await pointerUp(".s_compare_image_divider", { position: end });
//     await tick();

//     expect(getPosition()).toBe("75%");
// });

// test("a move after the release is ignored", async () => {
//     setupCompareImageTest();
//     await startInteractions(compareImageXml());

//     const start = getFrameCentre();
//     await pointerDown(".s_compare_image_divider", { position: start });
//     await moveBy(start, 100, 0);
//     await pointerUp(".s_compare_image_divider", { position: { x: start.x + 100, y: start.y } });
//     await moveBy(start, 150, 0);

//     expect(getPosition()).toBe("75%");
// });
