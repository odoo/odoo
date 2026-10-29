import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, manuallyDispatchProgrammaticEvent } from "@odoo/hoot-dom";
import { setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { switchToEditMode } from "../../helpers";
import { startInteractionsWithSnippet } from "../helpers";

describe.current.tags("interaction_dev");
setupInteractionWhiteList("website.references_carousel");

/**
 * The snippet stylesheet is not loaded in unit tests: give the strip a
 * measurable width, from which the number of clones derives.
 *
 * @param {HTMLElement} el
 */
function setStripWidth(el) {
    el.querySelector(".s_references_carousel_marquee_container").style.cssText =
        "display: flex; width: 400px;";
    el.querySelector(".s_references_carousel_marquee_item").style.cssText =
        "display: flex; flex: 0 0 auto; width: 100px;";
}

test("edit mode shows the single strip of logos, without clone nor animation", async () => {
    const { core } = await startInteractionsWithSnippet("s_references_carousel", {
        processHTML: setStripWidth,
    });
    // Frontend: the strip is cloned until it covers the container, then
    // animated.
    expect(".s_references_carousel_marquee_item_clone").toHaveCount(9);
    expect(".s_references_carousel").toHaveClass("s_references_carousel_ready");

    await switchToEditMode(core);
    // Every logo must stay visible and selectable exactly once.
    expect(".s_references_carousel_marquee_item").toHaveCount(1);
    expect(".s_references_carousel").not.toHaveClass("s_references_carousel_ready");
});

test("scrolling the page does not drive the strip in edit mode", async () => {
    const { core } = await startInteractionsWithSnippet("s_references_carousel", {
        processHTML: setStripWidth,
    });
    manuallyDispatchProgrammaticEvent(window, "scroll");
    await animationFrame();
    expect(".s_references_carousel").toHaveClass("s_references_carousel_page_scrolling");

    await switchToEditMode(core);
    manuallyDispatchProgrammaticEvent(window, "scroll");
    await animationFrame();
    expect(".s_references_carousel").not.toHaveClass("s_references_carousel_page_scrolling");
});
