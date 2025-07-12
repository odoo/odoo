import { expect, test } from "@odoo/hoot";
import { animationFrame, click, Deferred, queryOne, waitFor } from "@odoo/hoot-dom";
import { loadBundle } from "@web/core/assets";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { BuilderOptionsPlugin } from "@html_builder/core/builder_options_plugin";
import { Operation } from "@html_builder/core/operation";
import { setupHTMLBuilder } from "./helpers";

test.tags("desktop");
test("click just after drop is redispatched in next operation", async () => {
    const nextDef = new Deferred();
    patchWithCleanup(Operation.prototype, {
        next(fn, ...args) {
            const originalFn = fn;
            fn = async () => {
                await originalFn();
                nextDef.resolve();
            };
            expect.step(`next${args[0]?.shouldInterceptClick ? " should intercept" : ""}`);
            const res = super.next(fn, ...args);
            return res;
        },
    });
    patchWithCleanup(BuilderOptionsPlugin.prototype, {
        async onClick(ev) {
            expect.step("onClick");
            super.onClick(ev);
        },
        updateContainers(...args) {
            expect.step("updateContainers");
            super.updateContainers(...args);
        },
    });
    await setupHTMLBuilder("", {
        styleContent: /*css*/ `
            .o_loading_screen {
                position: absolute;
                inset: 0;
            }
            section {
                height: 100%; /* to easily target */
            }`,
    });

    // TODO: the next lines replicate website's `insertCategorySnippet` helper.
    // It should be moved to html_builder.
    await contains(".o-snippets-menu #snippet_groups .o_snippet_thumbnail_area").click();
    await animationFrame();
    await loadBundle("html_builder.iframe_add_dialog", {
        targetDoc: queryOne("iframe.o_add_snippet_iframe").contentDocument,
        js: false,
    });
    await waitFor(".o_add_snippet_dialog iframe.show.o_add_snippet_iframe");
    await contains(
        ".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap"
    ).click();
    await animationFrame();
    expect.verifySteps(["next should intercept"]); // On snippet selected

    await waitFor(":iframe .o_loading_screen");
    await click(":iframe", { position: { x: 200, y: 50 }, relative: true });
    expect.verifySteps(["next"]); // On click
    await nextDef;
    expect.verifySteps(["updateContainers"]); // End of drop, on addStep()
    await animationFrame();
    expect.verifySteps(["onClick", "next", "updateContainers"]); // On click redispatched
    await animationFrame();
    expect(".o-snippets-tabs .o-hb-btn.active").toHaveText("Edit");
});
