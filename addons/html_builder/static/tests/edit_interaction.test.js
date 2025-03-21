import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { EditInteractionPlugin } from "@html_builder/website_builder/plugins/edit_interaction_plugin";
import {
    addActionOption,
    addOption,
    confirmAddSnippet,
    defineWebsiteModels,
    setupWebsiteBuilder,
    setupWebsiteBuilderWithSnippet,
} from "./website_helpers";
import { click, waitFor } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";

defineWebsiteModels();

test("dropping a new snippet starts its interaction", async () => {
    const { openBuilderSidebar } = await setupWebsiteBuilder("", { openEditor: false });
    patchWithCleanup(EditInteractionPlugin.prototype, {
        setup() {
            super.setup();
            this.websiteEditService.update = () => expect.step("update");
        },
    });
    await openBuilderSidebar();
    await waitFor(".o-website-builder_sidebar.o_builder_sidebar_open");
    expect.verifySteps(["update"]);
    await contains(
        `.o-snippets-menu #snippet_groups .o_snippet[data-snippet-group='text'] .o_snippet_thumbnail_area`
    ).click();
    await confirmAddSnippet("s_title");
    expect.verifySteps(["update"]);
});

test("replacing a snippet starts the interaction of the new snippet", async () => {
    const { openBuilderSidebar } = await setupWebsiteBuilderWithSnippet("s_text_block", {
        openEditor: false,
    });
    patchWithCleanup(EditInteractionPlugin.prototype, {
        setup() {
            super.setup();
            this.websiteEditService.update = () => expect.step("update");
        },
    });
    await openBuilderSidebar();
    await waitFor(":iframe [data-snippet='s_text_block']");
    expect.verifySteps(["update"]);
    await click(`:iframe [data-snippet="s_text_block"]`);
    await contains(".btn.o_snippet_replace").click();
    await confirmAddSnippet("s_title");
    expect.verifySteps(["update"]);
});

test("ensure order of operations when hovering an option", async () => {
    addActionOption({
        customAction: {
            load: async () => {
                expect.step("load");
            },
            apply: ({ editingElement }) => {
                editingElement.classList.add("new_class");
                expect.step("apply");
            },
        },
    });
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderButton action="'customAction'"/>`,
    });
    patchWithCleanup(EditInteractionPlugin.prototype, {
        restartInteractions() {
            expect.step("restartInteractions");
        },
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    expect.verifySteps(["restartInteractions"]);
    await contains(":iframe .test-options-target").click();
    await contains("[data-action-id='customAction']").hover();
    expect.verifySteps(["load", "apply", "restartInteractions"]);
});

describe("exit builder", () => {
    beforeEach(async () => {
        const { openBuilderSidebar } = await setupWebsiteBuilderWithSnippet("s_text_block", {
            openEditor: false,
        });
        patchWithCleanup(EditInteractionPlugin.prototype, {
            setup() {
                super.setup();
                this.websiteEditService.stop = () => expect.step("stop");
            },
        });
        await openBuilderSidebar();
    });
    test("saving stops the interactions", async () => {
        await waitFor(":iframe [data-snippet='s_text_block']");
        await contains("[data-action='save']").click();
        await waitFor(".o-website-builder_sidebar:not(.o_builder_sidebar_open)");
        expect.verifySteps(["stop", "stop"]); // save stops & destroy also stops
    });
    test("discarding stops the interactions", async () => {
        await waitFor(":iframe [data-snippet='s_text_block']");
        await contains("[data-action='cancel']").click();
        await waitFor(".o-website-builder_sidebar:not(.o_builder_sidebar_open)");
        expect.verifySteps(["stop"]);
    });
});
