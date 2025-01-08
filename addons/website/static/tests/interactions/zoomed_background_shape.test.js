import { describe, expect, test } from "@odoo/hoot";
import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.zoomed_background_shape");
describe.current.tags("interaction_dev");

test("zoomed background shape test is not needed without zoom", async () => {
    const { core, el } = await startInteractions(`
        <div id="wrapwrap" style="width: 1000px;">
            <section class="s_faq_list pt56 pb56 o_colored_level" data-snippet="s_faq_list" data-name="FAQ List" style="position: relative;" data-oe-shape-data="{&quot;shape&quot;:&quot;web_editor/Airy/13_001&quot;,&quot;colors&quot;:{&quot;c1&quot;:&quot;#714B67&quot;,&quot;c4&quot;:&quot;#D6D6E7&quot;},&quot;flip&quot;:[],&quot;showOnMobile&quot;:false,&quot;shapeAnimationSpeed&quot;:&quot;0&quot;,&quot;animated&quot;:&quot;true&quot;}">
                <div class="o_we_shape o_web_editor_Airy_13_001 o_we_animated" style="background-image: url(&quot;/web_editor/shape/web_editor%2FAiry%2F13_001.svg?c1=%23714B67&amp;c4=%23D6D6E7&quot;);"/>
                <div style="min-height: 500px;">Some content</div>
            </section>
        </div>
    `);
    expect(core.interactions.length).toBe(1);
    const shapeEl = el.querySelector(".o_we_shape");
    expect(shapeEl.style.left).toBe("");
    expect(shapeEl.style.right).toBe("");
});

test("zoomed background shape test applies correction on zoom", async () => {
    const { core, el } = await startInteractions(`
        <div id="wrapwrap" style="width: 1000px; transform: scale(0.9997);">
            <section style="position: relative;" data-oe-shape-data="{&quot;shape&quot;:&quot;web_editor/Airy/13_001&quot;,&quot;colors&quot;:{&quot;c1&quot;:&quot;#714B67&quot;,&quot;c4&quot;:&quot;#D6D6E7&quot;},&quot;flip&quot;:[],&quot;showOnMobile&quot;:false,&quot;shapeAnimationSpeed&quot;:&quot;0&quot;,&quot;animated&quot;:&quot;true&quot;}">
                <div class="o_we_shape o_web_editor_Airy_13_001 o_we_animated" style="background-image: url(&quot;/web_editor/shape/web_editor%2FAiry%2F13_001.svg?c1=%23714B67&amp;c4=%23D6D6E7&quot;);"/>
                <div style="min-height: 500px;">Some content</div>
            </section>
        </div>
    `);
    expect(core.interactions.length).toBe(1);
    const shapeEl = el.querySelector(".o_we_shape");
    // Adjustment depends on window size during test.
    expect(shapeEl.style.left).toMatch(/\d+\.\d+px/);
    expect(shapeEl.style.right).toMatch(/\d+\.\d+px/);
    expect(shapeEl.style.left).toBe(shapeEl.style.right);
});
