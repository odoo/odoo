import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";

setupInteractionWhiteList("website.zoomed_background_shape");

describe.current.tags("interaction_dev");

test("zoomed_background_shape is not needed without zoom", async () => {
    const { core } = await startInteractions(`
        <div id="wrapwrap" style="width: 1000px;">
            <section class="s_faq_list pt56 pb56 o_colored_level" data-snippet="s_faq_list" data-name="FAQ List" style="position: relative;" data-oe-shape-data="{&quot;shape&quot;:&quot;html_builder/Airy/13_001&quot;,&quot;colors&quot;:{&quot;c1&quot;:&quot;#714B67&quot;,&quot;c4&quot;:&quot;#D6D6E7&quot;},&quot;flip&quot;:[],&quot;showOnMobile&quot;:false,&quot;shapeAnimationSpeed&quot;:&quot;0&quot;,&quot;animated&quot;:&quot;true&quot;}">
                <div class="o_we_shape o_html_builder_Airy_13_001 o_we_animated" style="background-image: url(&quot;/html_editor/shape/web_editor%2FAiry%2F13_001.svg?c1=%23714B67&amp;c4=%23D6D6E7&quot;);"/>
                <div style="min-height: 500px;">Some content</div>
            </section>
        </div>
    `);
    expect(core.interactions).toHaveLength(1);
    const shapeEl = queryOne(".o_we_shape");
    expect(shapeEl).not.toHaveAttribute("style", /left:/);
    expect(shapeEl).toHaveStyle({ left: "0px" });
    expect(shapeEl).not.toHaveAttribute("style", /right:/);
    expect(shapeEl).toHaveStyle({ right: "0px" });
});

// TODO: @mysterious-egg check if it s ok in mobile
test.tags("desktop");
test("zoomed_background_shape applies correction on zoom", async () => {
    const { core } = await startInteractions(`
        <div id="wrapwrap" style="width: 1000px; transform: scale(0.9997);">
            <section style="position: relative;" data-oe-shape-data="{&quot;shape&quot;:&quot;html_builder/Airy/13_001&quot;,&quot;colors&quot;:{&quot;c1&quot;:&quot;#714B67&quot;,&quot;c4&quot;:&quot;#D6D6E7&quot;},&quot;flip&quot;:[],&quot;showOnMobile&quot;:false,&quot;shapeAnimationSpeed&quot;:&quot;0&quot;,&quot;animated&quot;:&quot;true&quot;}">
                <div class="o_we_shape o_html_builder_Airy_13_001 o_we_animated" style="background-image: url(&quot;/html_editor/shape/web_editor%2FAiry%2F13_001.svg?c1=%23714B67&amp;c4=%23D6D6E7&quot;);"/>
                <div style="min-height: 500px;">Some content</div>
            </section>
        </div>
    `);
    expect(core.interactions).toHaveLength(1);
    const shapeEl = queryOne(".o_we_shape");
    // Adjustment depends on window size during test.
    expect(shapeEl).toHaveAttribute("style", /left:/);
    expect(shapeEl).not.toHaveStyle({ left: "0px" });
    expect(shapeEl).toHaveAttribute("style", /right:/);
    expect(shapeEl).not.toHaveStyle({ right: "0px" });
    expect(shapeEl).toHaveStyle({ left: shapeEl.style.right });
});
