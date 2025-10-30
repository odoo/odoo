import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
    addLegacyBuilderOption,
} from "@html_builder/../tests/helpers";
import { Builder } from "@html_builder/builder";
import { BuilderAction } from "@html_builder/core/builder_action";
import { SavePlugin } from "@html_builder/core/save_plugin";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-dom";
import { useState, xml } from "@odoo/owl";
import {
    contains,
    defineModels,
    fields,
    models,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

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
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".s_test";
            static template = xml`<BuilderButton action="'testAction'">Click</BuilderButton>`;
        }
    );
    await setupHTMLBuilder(`<section class="s_test">Test</section>`);
    await contains(":iframe .s_test").click();
    await contains("[data-action-id='testAction']").click();
    expect("[data-action-id='testAction']").toHaveClass("active");
    expect.verifySteps(["apply", "apply"]); // preview, apply
    await contains("[data-action-id='testAction']").click();
    expect("[data-action-id='testAction']").not.toHaveClass("active");
    expect.verifySteps(["apply"]); // clean
});

test("check Legacy Builder Option is supported", async () => {
    addLegacyBuilderOption({
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
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".s_test";
            static template = xml`<BuilderButton action="'testAction'" classAction="'custom-class'">Click</BuilderButton>`;
        }
    );
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
        static selector = ".test-options-target";
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
    addBuilderOption(TestOption);
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
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".s_test";
            static template = xml`<BuilderButton dataAttributeAction="'customerOrderIds'" dataAttributeActionValue="[100, 200]">Click</BuilderButton>`;
        }
    );
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
                    delete editingElement.dataset.value;
                }
            },
        });
    });

    test("useClickableBuilderComponent", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderButton action="'isPreviewing'" actionValue="true">Toggle</BuilderButton>`;
            }
        );
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
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderTextInput action="'isPreviewing'"/>`;
            }
        );
        await setupHTMLBuilder(`<section class="test-options-target">Homepage</section>`);
        await contains(":iframe .test-options-target").click();

        // apply
        await contains("[data-action-id='isPreviewing'] input").edit("truthy");
        expect.verifySteps(["apply true", "apply false"]);
    });

    test("useColorPickerBuilderComponent", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderColorPicker action="'isPreviewing'"/>`;
            }
        );
        await setupHTMLBuilder(`<section class="test-options-target">Homepage</section>`);
        await contains(":iframe .test-options-target").click();

        // apply
        await contains(".o_we_color_preview").click();
        await contains("button:contains(Custom)").click();
        await contains("button[data-color='600']").click();
        expect.verifySteps(["apply true", "apply false"]);
    });

    test("BuilderMany2One", async () => {
        class Test extends models.Model {
            _name = "test";
            _records = [
                { id: 1, name: "First" },
                { id: 2, name: "Second" },
                { id: 3, name: "Third" },
            ];
            name = fields.Char();
        }
        onRpc("test", "name_search", () => [
            [1, "First"],
            [2, "Second"],
            [3, "Third"],
        ]);

        defineModels([Test]);

        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderMany2One action="'isPreviewing'" model="'test'" limit="10" allowUnselect="true"/>`;
            }
        );
        await setupHTMLBuilder(`<section class="test-options-target">Homepage</section>`);
        await contains(":iframe .test-options-target").click();

        // apply
        await contains(".o_select_menu button").click();
        await contains(".o_select_menu button").click(); // issue with select menu + builder many2one in tests: does not load on first open
        await contains(".o_select_menu button").click();
        await contains(".o_select_menu_item[data-choice-index='0']").click();
        expect.verifySteps(["apply true", "apply false"]);

        // clean
        await contains(".o_select_menu + button > .oi-close").click();
        expect.verifySteps(["clean true", "clean false"]);
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

    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderButton action="'testReload'">Click</BuilderButton>`;
        }
    );
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
