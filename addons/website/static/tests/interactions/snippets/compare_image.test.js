import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, hover, pointerDown, pointerUp, queryOne } from "@odoo/hoot-dom";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.compare_image");

describe.current.tags("interaction_dev");

/**
 * The frontend stylesheet is not loaded in tests, so the frame is given its size
 * inline: it is the only box the interaction measures, and 400x200 makes every
 * expected position a round number.
 *
 * @param {string} [classes] added to the snippet root, e.g. the orientation
 */
const compareImageXml = (classes = "") => `
    <figure class="s_compare_image ${classes}" style="--compare-pos: 50%;">
        <div class="s_compare_image_frame" style="width: 400px; height: 200px;">
            <img class="s_compare_image_before" alt=""/>
            <img class="s_compare_image_after" alt=""/>
            <div class="s_compare_image_divider">
                <span class="s_compare_image_handle"/>
            </div>
        </div>
    </figure>
`;

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
    const { core } = await startInteractions(compareImageXml());

    expect(core.interactions).toHaveLength(1);
    expect(getPosition()).toBe("50%");
});

test("dragging the divider moves it by the distance covered", async () => {
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
    await startInteractions(compareImageXml("s_compare_image_horizontal"));

    const start = getFrameCentre();
    await pointerDown(".s_compare_image_divider", { position: start });
    await moveBy(start, 100, 0);

    expect(getPosition()).toBe("50%");

    // A quarter of the 200px frame.
    await moveBy(start, 0, 50);

    expect(getPosition()).toBe("75%");
});

test("the vertical divider is mirrored in RTL", async () => {
    await startInteractions(`<div dir="rtl">${compareImageXml()}</div>`);

    const start = getFrameCentre();
    await pointerDown(".s_compare_image_divider", { position: start });
    // The position is measured from the right edge, so it grows leftwards.
    await moveBy(start, -100, 0);

    expect(getPosition()).toBe("75%");
});

test("releasing the divider ends the drag", async () => {
    await startInteractions(compareImageXml());

    const start = getFrameCentre();
    await pointerDown(".s_compare_image_divider", { position: start });
    await moveBy(start, 100, 0);
    await pointerUp(".s_compare_image_divider", { position: { x: start.x + 100, y: start.y } });
    await moveBy(start, 150, 0);

    expect(getPosition()).toBe("75%");
});

test("a non-primary button does not start a drag", async () => {
    await startInteractions(compareImageXml());

    const start = getFrameCentre();
    await pointerDown(".s_compare_image_divider", { position: start, button: 2 });
    await moveBy(start, 100, 0);

    expect(getPosition()).toBe("50%");
});
