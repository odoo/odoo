import { describe, expect, test } from "@odoo/hoot";
import { click, queryAll, queryFirst, queryOne } from "@odoo/hoot-dom";
import { animationFrame, mockMatchMedia } from "@odoo/hoot-mock";
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

    expect(".o_marquee_item_clone").toHaveCount(EXPECTED_CLONE_COUNT);
    // The measured strip width drives the animation duration in CSS.
    expect(
        queryOne(".s_announcement_scroll_marquee_container").style.getPropertyValue(
            "--marquee-item-size"
        )
    ).toBe("100");
    // The animation only starts once the layout is computed, on the strip and
    // on each of its clones.
    expect(".s_announcement_scroll").toHaveClass("o_marquee_ready");
    expect(".o_marquee_item").toHaveCount(EXPECTED_CLONE_COUNT + 1);
});

test("the clones are decorative duplicates", async () => {
    await startInteractions(template);

    for (const cloneEl of queryAll(".o_marquee_item_clone")) {
        // Assistive technologies must read the announcement once, not once per
        // clone.
        expect(cloneEl).toHaveAttribute("aria-hidden", "true");
        // A clone is never a valid editing nor option target.
        expect(cloneEl).toHaveClass("o_not_editable");
        expect(cloneEl).toHaveClass("o_snippet_not_selectable");
    }
});

test("the links of the clones are left out of the tab order", async () => {
    await startInteractions(template.replace("Free Shipping", `<a href="/shop">Free Shipping</a>`));

    expect(".s_announcement_scroll_marquee_item:not(.o_marquee_item_clone) a").not.toHaveAttribute(
        "tabindex"
    );
    expect(".o_marquee_item_clone a").toHaveCount(EXPECTED_CLONE_COUNT);
    for (const linkEl of queryAll(".o_marquee_item_clone a")) {
        expect(linkEl).toHaveAttribute("tabindex", "-1");
    }
});

test("consecutive text strips are separated by a non-breaking space", async () => {
    await startInteractions(template);

    expect(queryFirst(".o_marquee_item_clone").textContent).toBe("\u00A0Free Shipping");
});

test("stopping the interaction restores the original markup", async () => {
    const { core } = await startInteractions(template);
    const containerEl = queryOne(".s_announcement_scroll_marquee_container");

    core.stopInteractions();
    expect(core.interactions).toHaveLength(0);

    // No leftover: clones are never saved with the page.
    expect(".o_marquee_item_clone").toHaveCount(0);
    expect(".s_announcement_scroll_marquee_item").toHaveCount(1);
    expect(containerEl.style.getPropertyValue("--marquee-item-size")).toBe("");
    expect(".s_announcement_scroll").not.toHaveClass("o_marquee_ready");
    expect(".o_marquee_item").toHaveCount(0);
});

test("a visitor can pause and resume the strip", async () => {
    const { core } = await startInteractions(
        template.replace(
            '<div class="s_announcement_scroll_marquee_container"',
            `<button class="o_marquee_pause o_btn_reset" title="Pause animation">
                <span class="o_marquee_pause_icon oi oi-filled" data-icon="pause"/>
                <span class="visually-hidden">Pause animation</span>
            </button>
            <div class="s_announcement_scroll_marquee_container"`
        )
    );
    expect(".o_marquee_pause").toHaveAttribute("title", "Pause animation");
    expect(".o_marquee_pause .visually-hidden").toHaveText("Pause animation");
    expect(".o_marquee_pause_icon").toHaveAttribute("data-icon", "pause");

    await click(".o_marquee_pause");
    await animationFrame();
    expect(".s_announcement_scroll").toHaveClass("o_marquee_paused");
    expect(".o_marquee_pause").toHaveAttribute("title", "Play animation");
    expect(".o_marquee_pause .visually-hidden").toHaveText("Play animation");
    expect(".o_marquee_pause_icon").toHaveAttribute("data-icon", "play_arrow");

    await click(".o_marquee_pause");
    await animationFrame();
    expect(".s_announcement_scroll").not.toHaveClass("o_marquee_paused");
    expect(".o_marquee_pause").toHaveAttribute("title", "Pause animation");

    // Paused when the page is saved: the button is saved as it was.
    await click(".o_marquee_pause");
    await animationFrame();
    core.stopInteractions();
    expect(".s_announcement_scroll").not.toHaveClass("o_marquee_paused");
    expect(".o_marquee_pause").toHaveAttribute("title", "Pause animation");
    expect(".o_marquee_pause .visually-hidden").toHaveText("Pause animation");
    expect(".o_marquee_pause_icon").toHaveAttribute("data-icon", "pause");
});

test("with reduced motion, the strip starts on its first item", async () => {
    mockMatchMedia({ "prefers-reduced-motion": "reduce" });
    await startInteractions(template);
    expect(queryOne(".s_announcement_scroll_marquee_container").style.transform).toBe(
        "translateX(0%)"
    );
});

test("with motion, the strip starts in the middle of the loop", async () => {
    mockMatchMedia({ "prefers-reduced-motion": "no-preference" });
    await startInteractions(template);
    expect(queryOne(".s_announcement_scroll_marquee_container").style.transform).toBe(
        "translateX(-50%)"
    );
});
