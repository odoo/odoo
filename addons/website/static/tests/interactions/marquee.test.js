import { describe, expect, test } from "@odoo/hoot";
import { queryAll, queryFirst, queryOne } from "@odoo/hoot-dom";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

// The shared `Marquee` interaction is covered through `s_announcement_scroll`,
// its first implementation.
setupInteractionWhiteList("website.announcement_scroll");

describe.current.tags("interaction_dev");

// A 100px strip in a 400px container needs `ceil(400 / 100) * 2 + 1` clones to
// cover twice the container (plus one for the reverse animation).
const EXPECTED_CLONE_COUNT = 9;

const template = /* html */ `
    <section class="s_announcement_scroll s_announcement_scroll_direction_left" role="marquee">
        <div class="s_announcement_scroll_marquee_container" style="display: flex; width: 400px;">
            <div class="o_not_editable s_announcement_scroll_marquee_item"
                style="flex: 0 0 auto; width: 100px;">Free Shipping</div>
        </div>
    </section>
`;

test("the strip is cloned until it covers the container", async () => {
    const { core } = await startInteractions(template);
    expect(core.interactions).toHaveLength(1);

    expect(".s_announcement_scroll_marquee_item_clone").toHaveCount(EXPECTED_CLONE_COUNT);
    // The measured strip width drives the animation duration in CSS.
    expect(
        queryOne(".s_announcement_scroll_marquee_container").style.getPropertyValue(
            "--marquee-item-size"
        )
    ).toBe("100");
    // The animation only starts once the layout is computed.
    expect(".s_announcement_scroll").toHaveClass("s_announcement_scroll_ready");
});

test("the clones are decorative duplicates", async () => {
    await startInteractions(template);

    for (const cloneEl of queryAll(".s_announcement_scroll_marquee_item_clone")) {
        // Assistive technologies must read the announcement once, not once per
        // clone.
        expect(cloneEl).toHaveAttribute("aria-hidden", "true");
        // A clone is never a valid editing nor option target.
        expect(cloneEl).toHaveClass("o_not_editable");
        expect(cloneEl).toHaveClass("o_snippet_not_selectable");
    }
});

test("consecutive text strips are separated by a non-breaking space", async () => {
    await startInteractions(template);

    expect(queryFirst(".s_announcement_scroll_marquee_item_clone").textContent).toBe(
        "\u00A0Free Shipping"
    );
});

test("stopping the interaction restores the original markup", async () => {
    const { core } = await startInteractions(template);
    const containerEl = queryOne(".s_announcement_scroll_marquee_container");

    core.stopInteractions();
    expect(core.interactions).toHaveLength(0);

    // No leftover: clones are never saved with the page.
    expect(".s_announcement_scroll_marquee_item_clone").toHaveCount(0);
    expect(".s_announcement_scroll_marquee_item").toHaveCount(1);
    expect(containerEl.style.getPropertyValue("--marquee-item-size")).toBe("");
    expect(".s_announcement_scroll").not.toHaveClass("s_announcement_scroll_ready");
});
