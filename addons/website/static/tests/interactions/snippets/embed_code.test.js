import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";

setupInteractionWhiteList("website.embed_code");

describe.current.tags("interaction_dev");

/* TODO Requires a way to inject a script in a fixture.
test("embed code executed only once", async () => {
    const { core } = await startInteractions(`
    <section class="s_embed_code text-center pt64 pb64 o_colored_level" data-snippet="s_embed_code" data-name="Embed Code">
        <template class="s_embed_code_saved"><script>expect.step("template");</script></template>
        <div class="s_embed_code_embedded container o_not_editable"><script>expect.step("div");</script></div>
    </section>
    `);
    expect(core.interactions).toHaveLength(1);
    expect.verifySteps(["div"]);
});
*/

test("embed_code resets on stop", async () => {
    const { core } = await startInteractions(`
        <section class="s_embed_code text-center pt64 pb64 o_colored_level" data-snippet="s_embed_code" data-name="Embed Code">
            <template class="s_embed_code_saved">
                <div>original</div>
            </template>
            <div class="s_embed_code_embedded container o_not_editable">
                <div>original</div>
            </div>
        </section>
    `);
    expect(core.interactions).toHaveLength(1);
    const embeddedEl = queryOne(".s_embed_code_embedded div");
    embeddedEl.textContent = "changed";
    expect(embeddedEl).toHaveText("changed");
    core.stopInteractions();
    expect(core.interactions).toHaveLength(0);
    expect(".s_embed_code_embedded div").toHaveText("original");
});
