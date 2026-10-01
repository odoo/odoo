import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, hover, pointerDown, pointerUp, queryOne } from "@odoo/hoot-dom";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

import { switchToEditMode } from "../../helpers";
import { compareImageXml, setupCompareImageTest } from "./helpers";

setupInteractionWhiteList("website.compare_image");

describe.current.tags("interaction_dev");

test("the divider cannot be dragged in edit mode", async () => {
    setupCompareImageTest();
    const { core } = await startInteractions(compareImageXml(), {
        waitForStart: true,
        editMode: true,
    });
    await switchToEditMode(core);

    // Without this the test would pass on an inactive interaction.
    expect(core.interactions).toHaveLength(1);

    const { left, top, width, height } = queryOne(".s_compare_image_frame").getBoundingClientRect();
    const start = { x: left + width / 2, y: top + height / 2 };
    await pointerDown(".s_compare_image_divider", { position: start });
    await hover(".s_compare_image_divider", { position: { x: start.x + 100, y: start.y } });
    await animationFrame();
    await pointerUp(".s_compare_image_divider", { position: { x: start.x + 100, y: start.y } });

    // The position is owned by the "Initial position" option, so the inline
    // style written in the markup has to survive the drag untouched.
    expect(queryOne(".s_compare_image").style.getPropertyValue("--compare-pos")).toBe("50%");
});
