import { BuilderAction } from "@html_builder/core/builder_action";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, Deferred, waitFor } from "@odoo/hoot-dom";
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
});
