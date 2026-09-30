import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { EditInteractionPlugin } from "@website/builder/plugins/edit_interaction_plugin";
import {
    addActionOption,
    addOption,
    defineWebsiteModels,
    setupWebsiteBuilder,
    setupWebsiteBuilderWithSnippet,
} from "./website_helpers";
import { waitFor } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { BuilderAction } from "@html_builder/core/builder_action";
import { confirmAddSnippet, waitForEndOfOperation } from "@html_builder/../tests/helpers";

defineWebsiteModels();

test("dropping a new snippet starts its interaction", async () => {
    const { openBuilderSidebar } = await setupWebsiteBuilder("", { openEditor: false });
    patchWithCleanup(EditInteractionPlugin.prototype, {
        setup() {
            super.setup();
            this.websiteEditService.refresh = () => expect.step("refresh");
        },
    });
    await openBuilderSidebar();
    await waitFor(".o-website-builder_sidebar.o_builder_sidebar_open");
    expect.verifySteps(["refresh"]);
    await contains(
        `.o-snippets-menu #snippet_groups .o_snippet[data-snippet-group='text'] .o_snippet_thumbnail_area`
    ).click();
    await confirmAddSnippet("s_title");
    await waitForEndOfOperation();
    expect.verifySteps(["refresh"]);
});

test("ensure order of operations when hovering an option", async () => {
    addActionOption({
        customAction: class extends BuilderAction {
            static id = "customAction";
            async load() {
                expect.step("load");
            }
            apply({ editingElement }) {
                editingElement.classList.add("new_class");
                expect.step("apply");
            }
        },
    });
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderButton action="'customAction'"/>`,
    });
    patchWithCleanup(EditInteractionPlugin.prototype, {
        refreshInteractions(element) {
            expect.step("refreshInteractions");
        },
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    expect.verifySteps(["refreshInteractions"]);
    await contains(":iframe .test-options-target").click();
    await contains("[data-action-id='customAction']").hover();
    expect.verifySteps(["load", "apply", "refreshInteractions"]);
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
