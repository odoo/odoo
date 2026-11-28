import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { hover, pointerDown, pointerUp, queryOne } from "@odoo/hoot-dom";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { defineStyle } from "@web/../tests/web_test_helpers";
import { getCompareImageXml } from "@website/../tests/interactions/snippets/helpers";

setupInteractionWhiteList("website.compare_image");

describe.current.tags("interaction_dev");

/**
 * The frontend stylesheet is not loaded in tests, so the frame is given its
 * size here: it is the only box the interaction measures, and 400x200 makes
 * every expected position a round number.
 */
beforeEach(() => defineStyle(/* css */ `.s_compare_image_frame { width: 400px; height: 200px; }`));

/**
 * Returns a point relative to the centre of the frame, where the divider
 * starts. It is measured on each call, since the frame only exists once the
 * test has started the interaction.
 *
 * @param {number} [dx]
 * @param {number} [dy]
 */
function getPoint(dx = 0, dy = 0) {
    const { left, top, width, height } = queryOne(".s_compare_image_frame").getBoundingClientRect();
    return { x: left + width / 2 + dx, y: top + height / 2 + dy };
}

function getPosition() {
    return queryOne(".s_compare_image").style.getPropertyValue("--s_compare_image-position");
}

/**
 * Moves the pointer over the divider, to a point relative to the centre of the
 * frame.
 *
 * @param {number} dx
 * @param {number} dy
 */
async function moveTo(dx, dy) {
    await hover(".s_compare_image_divider", { position: getPoint(dx, dy) });
}

test("dragging the divider follows the pointer within the frame", async () => {
    await startInteractions(getCompareImageXml());

    // Grabbed 50px off-centre, the divider keeps that gap instead of jumping.
    await pointerDown(".s_compare_image_divider", { position: getPoint(50, 0) });
    await moveTo(150, 0);
    expect(getPosition()).toBe("75%");

    await moveTo(-50, 0);
    expect(getPosition()).toBe("25%");

    await moveTo(1000, 0);
    expect(getPosition()).toBe("100%");

    await moveTo(-1000, 0);
    expect(getPosition()).toBe("0%");
});

test("the horizontal variant tracks the vertical axis, and is not mirrored in RTL", async () => {
    await startInteractions(
        `<div dir="rtl">${getCompareImageXml("s_compare_image_horizontal")}</div>`
    );

    await pointerDown(".s_compare_image_divider", { position: getPoint() });
    await moveTo(100, 0);
    expect(getPosition()).toBe("50%");

    await moveTo(0, 50);
    expect(getPosition()).toBe("75%");
});

test("the vertical divider is mirrored in RTL", async () => {
    await startInteractions(`<div dir="rtl">${getCompareImageXml()}</div>`);

    await pointerDown(".s_compare_image_divider", { position: getPoint() });
    await moveTo(-100, 0);
    expect(getPosition()).toBe("75%");
});

test("only a primary-button drag moves the divider, until released", async () => {
    await startInteractions(getCompareImageXml());

    await pointerDown(".s_compare_image_divider", { position: getPoint() });
    await moveTo(100, 0);
    await pointerUp(".s_compare_image_divider", { position: getPoint(100, 0) });
    await moveTo(150, 0);
    expect(getPosition()).toBe("75%");

    await pointerDown(".s_compare_image_divider", { position: getPoint(100, 0), button: 2 });
    await moveTo(150, 0);
    expect(getPosition()).toBe("75%");
});
