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
