import { expect, test } from "@odoo/hoot";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { EditInteractionPlugin } from "@html_builder/website_builder/plugins/edit_interaction_plugin";
import {
    confirmAddSnippet,
    defineWebsiteModels,
    openBuilderSidebar,
    setupWebsiteBuilder,
    setupWebsiteBuilderWithSnippet,
} from "./website_helpers";
import { animationFrame, click, waitFor } from "@odoo/hoot-dom";

defineWebsiteModels();

test("interactions are started when starting editing", async () => {
    await setupWebsiteBuilder("", { openEditor: false });
    let websiteEditService;
    patchWithCleanup(EditInteractionPlugin.prototype, {
        setup() {
            super.setup();
            this.websiteEditService.update = () => expect.step("update");
            websiteEditService = this.websiteEditService;
        },
    });
    await openBuilderSidebar();
    window.parent.document.dispatchEvent(
        new CustomEvent("transfer_website_edit_service", {
            detail: { websiteEditService },
        })
    );
    expect.verifySteps(["update"]);
});

test("dropping a new snippet starts its interaction", async () => {
    await setupWebsiteBuilder("", { openEditor: false });
    patchWithCleanup(EditInteractionPlugin.prototype, {
        setup() {
            super.setup();
            this.websiteEditService.update = () => expect.step("update");
        },
    });
    await openBuilderSidebar();
    await waitFor(".o-website-builder_sidebar.o_builder_sidebar_open");
    expect.verifySteps([]);

    await contains(
        `.o-snippets-menu #snippet_groups .o_snippet[data-snippet-group='text'] .o_snippet_thumbnail_area`
    ).click();
    await confirmAddSnippet("s_title");
    expect.verifySteps(["update"]);
});

test("replacing a snippet starts the interaction of the new snippet", async () => {
    await setupWebsiteBuilderWithSnippet("s_text_block", { openEditor: false });
    patchWithCleanup(EditInteractionPlugin.prototype, {
        setup() {
            super.setup();
            this.websiteEditService.update = () => expect.step("update");
        },
    });
    await openBuilderSidebar();
    await waitFor(":iframe [data-snippet='s_text_block']");
    expect.verifySteps([]);
    await click(`:iframe [data-snippet="s_text_block"]`);
    await contains(".btn.o_snippet_replace").click();
    await confirmAddSnippet("s_title");
    expect.verifySteps(["update"]);
});

test("removing a snippet stops its interaction", async () => {
    await setupWebsiteBuilderWithSnippet("s_title", { openEditor: false });
    patchWithCleanup(EditInteractionPlugin.prototype, {
        setup() {
            super.setup();
            this.websiteEditService.stop = () => expect.step("stop");
        },
    });
    await openBuilderSidebar();
    await waitFor(":iframe [data-snippet='s_title']");
    expect.verifySteps([]);
    await click(`:iframe [data-snippet="s_title"]`);
    await contains(".btn.oe_snippet_remove").click();
    await animationFrame();
    expect.verifySteps(["stop"]);
});

test("throw if edit interactions are started but website_edit service hasn't started", async () => {
    await setupWebsiteBuilder("", { openEditor: false });
    let plugin;
    patchWithCleanup(EditInteractionPlugin.prototype, {
        setup() {
            super.setup();
            this.websiteEditService = undefined;
            plugin = this;
        },
    });
    await openBuilderSidebar();
    expect(() => plugin.startInteractions()).toThrow("website edit service not loaded");
});

test("throw if edit interactions are stopped but website_edit service hasn't started", async () => {
    await setupWebsiteBuilder("", { openEditor: false });
    let plugin;
    patchWithCleanup(EditInteractionPlugin.prototype, {
        setup() {
            super.setup();
            this.websiteEditService = undefined;
            plugin = this;
        },
    });
    await openBuilderSidebar();
    expect(() => plugin.stopInteractions()).toThrow("website edit service not loaded");
});
