import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { describe, expect, test } from "@odoo/hoot";
import { switchToEditMode } from "../../helpers";
import { queryAll } from "@odoo/hoot-dom";
import { defaultCarouselStyleSnippet } from "./carousel_helpers";

setupInteractionWhiteList("website.carousel_edit");

describe.current.tags("interaction_dev");

test("[EDIT] carousel_edit resets slide to attributes", async () => {
    const { core } = await startInteractions(defaultCarouselStyleSnippet("true", 3000), {
        waitForStart: true,
        editMode: true,
    });
    await switchToEditMode(core);

    expect(core.interactions).toHaveLength(1);
    const controlEls = queryAll(".carousel-control-prev, .carousel-control-next");
    const indicatorEls = queryAll(".carousel-indicators > *");
    for (const controlEl of controlEls) {
        expect(controlEl).not.toHaveAttribute("data-bs-slide");
    }
    for (const indicatorEl of indicatorEls) {
        expect(indicatorEl).not.toHaveAttribute("data-bs-slide-to");
    }

    core.stopInteractions();

    expect(core.interactions).toHaveLength(0);
    for (const controlEl of controlEls) {
        expect(controlEl).toHaveAttribute("data-bs-slide");
    }
    for (const indicatorEl of indicatorEls) {
        expect(indicatorEl).toHaveAttribute("data-bs-slide-to");
    }
});
