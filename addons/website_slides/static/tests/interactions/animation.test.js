import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.animation");
describe.current.tags("interaction_dev");

test("on scroll animation changes based on scroll", async () => {
    const { core } = await startInteractions(`
        <div id="wrapwrap" style="overflow: scroll; max-height: 100%;">
            <div style="min-height: 2000px;">Tall stuff</div>
            <div class="o_wslide_fs_article_content">
                <div class="o_anim_fade_in o_animate o_animate_on_scroll" style="min-height: 500px; animation-duration: 5s"
                    data-scroll-zone-start="0" data-scroll-zone-end="100"
                >Animated</div>
            </div>
            <div style="min-height: 2000px;">Tall stuff</div>
        </div>
    `);
    expect(core.interactions).toHaveLength(1);
    const scrollEl = queryOne(".o_wslide_fs_article_content");
    expect(core.interactions[0].interaction.scrollingElement).toBe(scrollEl);
});
