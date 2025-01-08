import { describe, expect, test } from "@odoo/hoot";
import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.embed_code");
describe.current.tags("interaction_dev");

/* TODO Requires a way to inject a script in a fixture.
test("embed code executed only once", async () => {
    const { core, el } = await startInteractions(`
    <section class="s_embed_code text-center pt64 pb64 o_colored_level" data-snippet="s_embed_code" data-name="Embed Code">
        <template class="s_embed_code_saved"><script>expect.step("template");</script></template>
        <div class="s_embed_code_embedded container o_not_editable"><script>expect.step("div");</script></div>
    </section>
    `);
    expect(core.interactions.length).toBe(1);
    expect.verifySteps(["div"]);
});
*/

test("embed code resets on stop", async () => {
    const { core, el } = await startInteractions(`
    <section class="s_embed_code text-center pt64 pb64 o_colored_level" data-snippet="s_embed_code" data-name="Embed Code">
        <template class="s_embed_code_saved"><div>original</div></template>
        <div class="s_embed_code_embedded container o_not_editable"><div>original</div></div>
    </section>
    `);
    expect(core.interactions.length).toBe(1);
    let embeddedEl = el.querySelector(".s_embed_code_embedded div");
    embeddedEl.textContent = "changed";
    expect(embeddedEl.textContent).toBe("changed");
    core.stopInteractions();
    expect(core.interactions.length).toBe(0);
    embeddedEl = el.querySelector(".s_embed_code_embedded div");
    expect(embeddedEl.textContent).toBe("original");
});
