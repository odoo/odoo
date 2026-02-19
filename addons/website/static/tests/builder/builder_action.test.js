import { onWillStart, xml } from "@odoo/owl";
import { beforeEach, expect, test } from "@odoo/hoot";
import { advanceTime, animationFrame, click, Deferred, queryOne, waitFor } from "@odoo/hoot-dom";
import { Builder } from "@html_builder/builder";
import { addBuilderAction, addBuilderOption } from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { expandToolbar } from "@html_editor/../tests/_helpers/toolbar";
import { contains, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { addPlugin, defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { WebsiteBuilderClientAction } from "@website/client_actions/website_preview/website_builder_action";

beforeEach(defineWebsiteModels);

test("trigger mobile view", async () => {
    await setupWebsiteBuilder(`<h1> Homepage </h1>`);
    expect(".o_website_preview.o_is_mobile").toHaveCount(0);
    await contains("button[data-action='mobile']").click();
    expect(".o_website_preview.o_is_mobile").toHaveCount(1);
});

test("top window url in action context parameter", async () => {
    let websiteBuilder;
    patchWithCleanup(WebsiteBuilderClientAction.prototype, {
        setup() {
            websiteBuilder = this;
            this.props.action.context = {
                params: {
                    path: "/web/content/",
                },
            };
            super.setup();
        },
    });
    await setupWebsiteBuilder(`<h1> Homepage </h1>`);
    expect(websiteBuilder.initialUrl).toBe("/website/force/1?path=%2F");
});

test("getRecordInfo retrieves the info from the #wrap element", async () => {
    class TestPlugin extends Plugin {
        static id = "test";
        resources = {
            user_commands: [
                {
                    id: "test_cmd",
                    run: () => {
                        const recordInfo = this.config.getRecordInfo();
                        expect.step(`getRecordInfo ${JSON.stringify(recordInfo)}`);
                    },
                },
            ],
            toolbar_groups: { id: "test_group" },
            toolbar_items: [
                {
                    id: "test_btn",
                    groupId: "test_group",
                    commandId: "test_cmd",
                    description: "Test Button",
                },
            ],
        };
    }
    addPlugin(TestPlugin);

    const { getEditor } = await setupWebsiteBuilder(`<p>plop</p>`);
    const editor = getEditor();
    const p = editor.editable.querySelector("p");
    setSelection({
        anchorNode: p.firstChild,
        anchorOffset: 0,
        focusOffset: 4,
    });

    await waitFor(".o-we-toolbar");
    await expandToolbar();
    await click(".o-we-toolbar .btn[name=test_btn]");

    expect.verifySteps(['getRecordInfo {"resModel":"ir.ui.view","resId":"539","field":"arch"}']);
});

test("elements within iframe can't be clicked while the builder is being set up", async () => {
    const def = new Deferred();
    patchWithCleanup(WebsiteBuilderClientAction.prototype, {
        async loadIframeAndBundles(isEditing) {
            super.loadIframeAndBundles(isEditing);
            await def;
        },
    });
    await setupWebsiteBuilder(
        `<section class="test-section"><button onclick="window.step()">Click me</button></section>`,
        { openEditor: false }
    );
    const iframeEl = queryOne("iframe");
    iframeEl.contentWindow.step = () => expect.step("button clicked");
    await contains(":iframe .test-section button").click();
    expect.verifySteps(["button clicked"]);
    // Reimplementation of openBuilderSidebar().
    await click(".o-website-btn-custo-primary");
    // The button should not be clickable.
    await expect(click(":iframe .test-section button")).rejects.toThrow(
        `found 0 elements instead of 1: 1 matching ":iframe .test-section button" (1 iframe element), including 0 interactive elements`
    );
    expect.verifySteps([]);
    def.resolve();
    await advanceTime(200);
    await contains(":iframe .test-section button").click();
    await animationFrame();
    expect.verifySteps(["button clicked"]);
});

test("Builder is disabled when reloading", async () => {
    onRpc("ir.ui.view", "save", () => true);
    addBuilderAction({
        TestReloadAction: class extends BuilderAction {
            static id = "testReload";
            setup() {
                this.reload = {};
            }
            isApplied({ editingElement }) {
                return editingElement.dataset.applied === "true";
            }
            async apply({ editingElement }) {
                editingElement.dataset.applied = "true";
            }
            clean({ editingElement }) {
                editingElement.dataset.applied = "false";
            }
        },
    });

    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".target";
            static template = xml`<BuilderButton action="'testReload'">Reload editor</BuilderButton>`;
        }
    );
    const { waitSidebarUpdated } = await setupWebsiteBuilder(
        `<section class="target">Section</section>`
    );
    const def = new Deferred();
    patchWithCleanup(Builder.prototype, {
        setup() {
            super.setup();
            onWillStart(async () => {
                await def;
            });
        },
    });
    await contains(":iframe .target").click();
    await waitSidebarUpdated();
    await contains(".options-container [data-action-id='testReload']").click();
    expect(".o-website-builder_sidebar .o_builder_disabled").toHaveCount(1);
    // when builder is disabled we can't go to another tab, or do anything else
    // in the builder
    await contains(".o-snippets-tabs [data-name='blocks']").click();
    expect(".o-snippets-tabs [data-name='customize']").toHaveClass("active");
    // new instance of the builder shouldn't be disabled
    def.resolve();
    await waitSidebarUpdated();
    expect(".o-website-builder_sidebar .o_builder_disabled").toHaveCount(0);
    await contains(".o-snippets-tabs [data-name='blocks']").click();
    expect(".o-snippets-tabs [data-name='blocks']").toHaveClass("active");
});
