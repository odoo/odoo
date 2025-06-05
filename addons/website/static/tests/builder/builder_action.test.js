import { BuilderAction } from "@html_builder/core/builder_action";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { advanceTime, animationFrame, click, Deferred, queryOne, waitFor } from "@odoo/hoot-dom";
import { useState, xml } from "@odoo/owl";
import { Plugin } from "@html_editor/plugin";
import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { expandToolbar } from "@html_editor/../tests/_helpers/toolbar";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { addPlugin, defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { WebsiteBuilderClientAction } from "@website/client_actions/website_preview/website_builder_action";
import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { SavePlugin } from "@html_builder/core/save_plugin";
import { Builder } from "@html_builder/builder";

describe("website tests", () => {
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

        expect.verifySteps([
            'getRecordInfo {"resModel":"ir.ui.view","resId":"539","field":"arch"}',
        ]);
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
});

describe.tags("desktop");
describe("HTML builder tests", () => {
    class TestAction extends BuilderAction {
        static id = "testAction";
        isApplied({ editingElement }) {
            return editingElement.classList.contains("applied");
        }
        apply({ editingElement }) {
            editingElement.classList.toggle("applied");
            expect.step("apply");
        }
    }
    beforeEach(() => {
        addBuilderAction({
            TestAction,
        });
    });

    test("apply is called if clean is not defined", async () => {
        addBuilderOption({
            selector: ".s_test",
            template: xml`<BuilderButton action="'testAction'">Click</BuilderButton>`,
        });
        await setupHTMLBuilder(`<section class="s_test">Test</section>`);
        await contains(":iframe .s_test").click();
        await contains("[data-action-id='testAction']").click();
        expect("[data-action-id='testAction']").toHaveClass("active");
        expect.verifySteps(["apply", "apply"]); // preview, apply
        await contains("[data-action-id='testAction']").click();
        expect("[data-action-id='testAction']").not.toHaveClass("active");
        expect.verifySteps(["apply"]); // clean
    });

    test("custom action and shorthand action: clean actions are independent, apply is called on custom action if clean is not defined", async () => {
        addBuilderOption({
            selector: ".s_test",
            template: xml`<BuilderButton action="'testAction'" classAction="'custom-class'">Click</BuilderButton>`,
        });
        await setupHTMLBuilder(`<section class="s_test">Test</section>`);
        await contains(":iframe .s_test").click();
        await contains("[data-action-id='testAction']").click();
        expect("[data-action-id='testAction']").toHaveClass("active");
        expect.verifySteps(["apply", "apply"]); // preview, apply
        await contains("[data-action-id='testAction']").click();
        expect("[data-action-id='testAction']").not.toHaveClass("active");
        expect.verifySteps(["apply"]); // clean
    });

    test("Prepare is triggered on props updated", async () => {
        const newPropDeferred = new Deferred();
        let prepareDeferred = new Promise((r) => r());
        class TestOption extends BaseOptionComponent {
            static template = xml`<BuilderCheckbox action="'customAction'" actionParam="state.param"/>`;
            static props = {};
            setup() {
                super.setup();
                this.state = useState({ param: "old param" });
                newPropDeferred.then(() => {
                    this.state.param = "new param";
                });
            }
        }
        class CustomAction extends BuilderAction {
            static id = "customAction";
            async prepare() {
                await prepareDeferred;
                expect.step("prepare");
            }
            apply() {}
        }
        addBuilderAction({
            CustomAction,
        });
        addBuilderOption({
            OptionComponent: TestOption,
            selector: ".test-options-target",
        });
        await setupHTMLBuilder(`<section class="test-options-target">Homepage</section>`);
        await contains(":iframe .test-options-target").click();
        expect.verifySteps(["prepare"]);
        prepareDeferred = new Deferred();
        // Update prop
        newPropDeferred.resolve();
        await animationFrame();
        expect.verifySteps([]);
        prepareDeferred.resolve();
        await animationFrame();
        expect.verifySteps(["prepare"]);
    });

    test("Data Attribute action works with non string values", async () => {
        addBuilderOption({
            selector: ".s_test",
            template: xml`<BuilderButton dataAttributeAction="'customerOrderIds'" dataAttributeActionValue="[100, 200]">Click</BuilderButton>`,
        });
        await setupHTMLBuilder(`<section class="s_test">Test</section>`);
        await contains(":iframe .s_test").click();
        await contains(".we-bg-options-container button:contains('Click')").click();
        expect(".we-bg-options-container button:contains('Click')").toHaveClass("active");
        expect(":iframe .s_test").toHaveAttribute("data-customer-order-ids", "100,200");
    });

    describe("isPreviewing is passed to action's apply and clean", () => {
        beforeEach(async () => {
            addBuilderAction({
                IsPreviewingAction: class extends BuilderAction {
                    static id = "isPreviewing";
                    isApplied({ editingElement }) {
                        return editingElement.classList.contains("o_applied");
                    }

                    getValue({ editingElement }) {
                        return editingElement.dataset.value;
                    }

                    apply({ isPreviewing, editingElement, value }) {
                        expect.step(`apply ${isPreviewing}`);
                        editingElement.classList.add("o_applied");
                        editingElement.dataset.value = value;
                    }

                    clean({ isPreviewing, editingElement }) {
                        expect.step(`clean ${isPreviewing}`);
                        editingElement.classList.remove("o_applied");
                    }
                },
            });
        });

        test("useClickableBuilderComponent", async () => {
            addBuilderOption({
                selector: ".test-options-target",
                template: xml`<BuilderButton action="'isPreviewing'" actionValue="true">Toggle</BuilderButton>`,
            });
            await setupHTMLBuilder(`<section class="test-options-target">Homepage</section>`);
            await contains(":iframe .test-options-target").click();

            // apply
            await contains("[data-action-id='isPreviewing']").click();
            expect.verifySteps(["apply true", "apply false"]);

            // Hover something else, making sure we have a preview on next click
            await contains(":iframe .test-options-target").click();

            // clean
            await contains("[data-action-id='isPreviewing']").click();
            expect.verifySteps(["clean true", "clean false"]);
        });

        test("useInputBuilderComponent", async () => {
            addBuilderOption({
                selector: ".test-options-target",
                template: xml`<BuilderTextInput action="'isPreviewing'"/>`,
            });
            await setupHTMLBuilder(`<section class="test-options-target">Homepage</section>`);
            await contains(":iframe .test-options-target").click();

            // apply
            await contains("[data-action-id='isPreviewing'] input").edit("truthy");
            expect.verifySteps(["apply true", "apply false"]);
        });
    });

    test("reload action: apply, clean save and reload are called in the right order (async)", async () => {
        let reloadDef, applyDef, cleanDef;
        patchWithCleanup(SavePlugin.prototype, {
            async save() {
                expect.step("save sync");
                await super.save();
                expect.step("save async");
            },
            async saveView() {
                return new Promise((resolve) => setTimeout(resolve, 10));
            },
        });
        patchWithCleanup(Builder.prototype, {
            setup() {
                super.setup();
                this.editor.config.reloadEditor = async () => {
                    await new Promise((resolve) => setTimeout(resolve, 10));
                    expect.step("reload");
                    reloadDef.resolve();
                };
            },
        });
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
                    expect.step("apply sync");
                    await applyDef;
                    expect.step("apply async");
                    editingElement.dataset.applied = "true";
                }
                async clean({ editingElement }) {
                    expect.step("clean sync");
                    await cleanDef;
                    expect.step("clean async");
                    editingElement.dataset.applied = "false";
                }
            },
        });

        addBuilderOption({
            selector: ".test-options-target",
            template: xml`<BuilderButton action="'testReload'">Click</BuilderButton>`,
        });
        await setupHTMLBuilder(`<section class="test-options-target">Test</section>`);
        await contains(":iframe .test-options-target").click();

        // Apply
        reloadDef = new Deferred();
        applyDef = new Deferred();
        await contains("[data-action-id='testReload']").click();
        expect.verifySteps(["apply sync"]);
        applyDef.resolve();
        await reloadDef;
        expect.verifySteps(["apply async", "save sync", "save async", "reload"]);

        // Clean
        reloadDef = new Deferred();
        cleanDef = new Deferred();
        await contains("[data-action-id='testReload']").click();
        expect.verifySteps(["clean sync"]);
        cleanDef.resolve();
        await reloadDef;
        expect.verifySteps(["clean async", "save sync", "save async", "reload"]);
    });
});
