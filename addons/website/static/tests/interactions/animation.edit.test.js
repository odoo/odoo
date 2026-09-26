import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { enableTransitions } from "@odoo/hoot-mock";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { switchToEditMode } from "@website/../tests/helpers";

setupInteractionWhiteList("website.animation");

describe.current.tags("interaction_dev");

test("[EDIT] On-Appearance animations are reset in edit mode", async () => {
    enableTransitions();

    const { core } = await startInteractions(`
        <span class="o_animate o_anim_fade_in" style="animation-delay: 10s;">
            Animated Text
        </span>`);

    expect(core.interactions).toHaveLength(1);

    const animatedText = queryOne(".o_animate");
    expect(animatedText).not.toHaveStyle({ animationName: "dummy-none" });

    await switchToEditMode(core);
    expect(animatedText).toHaveStyle({ animationName: "dummy-none" });
    expect(animatedText).not.toHaveStyle({ "animation-play-state": "paused" });
});

test("[EDIT] the On-Appearance animation reset survives an interaction update", async () => {
    enableTransitions();

    const { core } = await startInteractions(`
        <span class="o_animate o_anim_fade_in">
            Animated Text
        </span>`);

    await switchToEditMode(core);

    const animatedText = queryOne(".o_animate");
    expect(animatedText).toHaveStyle({ animationName: "dummy-none" });

    // The animation options clear "animation-name" to play the animation (see
    // "forceAnimation"), and the editor updates the interactions on every
    // normalization: the reset has to be re-applied then.
    animatedText.style.animationName = "";
    core.interactions[0].updateContent();

    expect(animatedText).toHaveStyle({ animationName: "dummy-none" });
    expect(animatedText).not.toHaveStyle({ "animation-play-state": "paused" });
});

test("[EDIT] On-Scroll animations are not reset in edit mode", async () => {
    enableTransitions();

    const { core } = await startInteractions(`
        <span class="o_animate o_animate_on_scroll o_anim_fade_in">
            Animated Text
        </span>`);

    await switchToEditMode(core);

    // Those animations are driven by the scroll position, they never play on
    // their own: there is nothing to prevent in edit mode.
    const animatedText = queryOne(".o_animate");
    expect(animatedText).not.toHaveStyle({ animationName: "dummy-none" });
});
