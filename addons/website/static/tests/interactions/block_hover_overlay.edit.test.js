import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { queryOne } from "@odoo/hoot-dom";
import { patch } from "@web/core/utils/patch";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { BlockHoverOverlayEdit } from "@website/interactions/block_hover_overlay.edit";
import { switchToEditMode } from "../helpers";

setupInteractionWhiteList("website.block_hover_overlay_edit");

describe.current.tags("interaction_dev");

patch(BlockHoverOverlayEdit.prototype, {
    refreshOverlays() {
        expect.step("refresh overlays");
    },
});

function dispatchTransitionEnd(el, propertyName) {
    const event = new Event("transitionend", { bubbles: true });
    Object.defineProperty(event, "propertyName", { value: propertyName });
    el.dispatchEvent(event);
}

test("refresh overlays only after the block transform transition", async () => {
    const { core } = await startInteractions(
        `<div class="o_block_hover o_block_hover_translate"><span>Child</span></div>`,
        { waitForStart: true, editMode: true }
    );
    await switchToEditMode(core);
    expect(core.interactions).toHaveLength(1);

    const blockEl = queryOne(".o_block_hover");
    dispatchTransitionEnd(blockEl, "opacity");
    dispatchTransitionEnd(queryOne(".o_block_hover span"), "transform");
    await animationFrame();
    expect.verifySteps([]);

    dispatchTransitionEnd(blockEl, "transform");
    await animationFrame();
    expect.verifySteps(["refresh overlays"]);
});

test("overlay-only blocks do not start the overlay refresh interaction", async () => {
    const { core } = await startInteractions(
        `<div class="o_block_hover o_block_hover_overlay">Block</div>`,
        { waitForStart: true, editMode: true }
    );
    await switchToEditMode(core);
    expect(core.interactions).toHaveLength(0);
});
