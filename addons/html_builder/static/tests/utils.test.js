import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, Deferred, delay, queryOne } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains, onRpc } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

describe("useDomState", () => {
    test("Should not update the state of an async useDomState if a new step has been made", async () => {
        let currentResolve;
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<div t-att-data-letter="getLetter()"/>`;
                setup() {
                    super.setup(...arguments);
                    this.state = useDomState(async () => {
                        const letter = await new Promise((resolve) => {
                            currentResolve = resolve;
                        });
                        return {
                            delay: `${letter}`,
                        };
                    });
                }
                getLetter() {
                    expect.step(`state: ${this.state.delay}`);
                    return this.state.delay;
                }
            }
        );
        const { getEditor } = await setupHTMLBuilder(`<div class="test-options-target">a</div>`);
        await animationFrame();
        await contains(":iframe .test-options-target").click();
        const editor = getEditor();
        const resolve1 = currentResolve;
        resolve1("x");
        await animationFrame();

        editor.editable.querySelector(".test-options-target").textContent = "b";
        editor.shared.history.addStep();
        const resolve2 = currentResolve;
        editor.editable.querySelector(".test-options-target").textContent = "c";
        editor.shared.history.addStep();
        const resolve3 = currentResolve;

        resolve3("z");
        await animationFrame();
        resolve2("y");
        await animationFrame();
        expect.verifySteps(["state: x", "state: z"]);
    });
});

describe("waitSidebarUpdated", () => {
    test("wait for the operations to end, the async useDomState to be updated, and the new component with async useDomState to be mounted", async () => {
        const delayAmount = 42;
        let deferred;
        addBuilderAction({
            testAction: class extends BuilderAction {
                static id = "testAction";
                isApplied({ editingElement, value }) {
                    return editingElement.dataset.value == value;
                }
                async apply({ editingElement, value }) {
                    await delay(delayAmount);
                    await deferred;
                    editingElement.dataset.value = value;
                }
            },
        });
        class TestSubComponent extends BaseOptionComponent {
            static template = xml`
                <div class="test-value-sub">
                    <t t-out="state.value"/>
                </div>
            `;
            setup() {
                super.setup();
                this.state = useDomState(async (el) => {
                    await delay(delayAmount);
                    await deferred;
                    return { value: el.dataset.value };
                });
            }
        }
        class TestOptionComponent extends BaseOptionComponent {
            static selector = "div.test";
            static template = xml`
                <div class="test-value-parent">
                    <t t-out="state.value"/>
                </div>
                <div class="test-button-1">
                    <BuilderButton action="'testAction'" actionValue="'b'">b</BuilderButton>
                </div>
                <div class="test-button-2">
                    <BuilderButton id="'button_2_opt'" action="'testAction'" actionValue="'c'">c</BuilderButton>
                </div>
                <t t-if="state.showOther and isActiveItem('button_2_opt')">
                    <TestSubComponent/>
                </t>
            `;
            static components = { TestSubComponent };
            setup() {
                super.setup();
                this.state = useDomState(async (el) => {
                    await delay(delayAmount);
                    await deferred;
                    return { value: el.dataset.value, showOther: el.dataset.value === "c" };
                });
            }
        }
        addBuilderOption(TestOptionComponent);
        const { waitSidebarUpdated } = await setupHTMLBuilder(
            `<div class="test" data-value="a">a</div>`
        );

        deferred = new Deferred();
        await contains(":iframe div.test").click();
        expect(".test-value-parent").toHaveCount(0);
        deferred.resolve();

        await waitSidebarUpdated();
        expect(".test-value-parent").toHaveText("a");

        deferred = new Deferred();
        await contains(".test-button-1 button").click();
        expect(".test-value-parent").toHaveText("a");
        expect(".test-button-3").toHaveCount(0);
        deferred.resolve();

        await waitSidebarUpdated();
        expect(".test-value-parent").toHaveText("b");
        expect(".test-value-sub").toHaveCount(0);

        deferred = new Deferred();
        await contains(".test-button-2 button").click();
        expect(".test-value-parent").toHaveText("b");
        expect(".test-value-sub").toHaveCount(0);
        deferred.resolve();

        await waitSidebarUpdated();
        expect(".test-value-parent").toHaveText("c");
        expect(".test-value-sub").toHaveText("c");
    });
});

test("UI is blocked when doing the reloadable operation", async () => {
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
                await delay(100);
                editingElement.dataset.applied = "true";
            }
            clean({ editingElement }) {
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

    const { waitSidebarUpdated } = await setupHTMLBuilder(
        `<div class="test-options-target">Target</div>`
    );
    await contains(":iframe .test-options-target").click();
    await contains(".options-container [data-action-id='testReload']").click();
    expect(".o_blockUI").toHaveCount(1);
    await waitSidebarUpdated();
    expect(".o_blockUI").toHaveCount(0);
});

test("System should not crash if an asynchronous useDomState is working with removed editing element", async () => {
    let useDomStateStarted;
    let editingElRemoved;
    class TestOptionComponent extends BaseOptionComponent {
        static template = xml`<BuilderButton t-if="state.showOption" classAction="'y'">Click</BuilderButton>`;
        static selector = "div.test";
        setup() {
            super.setup();
            this.state = useDomState(async (el) => {
                if (useDomStateStarted) {
                    useDomStateStarted.resolve();
                }
                await editingElRemoved?.promise;
                return { showOption: !!el.parentElement.ownerDocument.defaultView };
            });
        }
    }
    addBuilderOption(TestOptionComponent);
    const { waitSidebarUpdated } = await setupHTMLBuilder(`<div class="test">a</div>`);
    await contains(":iframe .test").click();
    await waitSidebarUpdated();
    useDomStateStarted = Promise.withResolvers();
    editingElRemoved = Promise.withResolvers();
    await contains("[data-class-action='y']").click();
    await useDomStateStarted.promise;
    queryOne(":iframe .test").remove();
    editingElRemoved.resolve();
});

test("Shouldn't reload(save, etc) when a reload is canceled", async () => {
    const { promise, resolve } = Promise.withResolvers();

    onRpc("ir.ui.view", "save", async () => {
        await promise;
        expect.step("save");
        return true;
    });
    addBuilderAction({
        TestCancelReloadAction: class extends BuilderAction {
            static id = "testCancelReload";
            setup() {
                this.reload = {};
            }
            load({ editingElement }) {
                return { shouldReload: editingElement.classList.contains("should_reload") };
            }
            async apply({ editingElement, loadResult }) {
                editingElement.dataset.applied = "true";
                if (!loadResult.shouldReload) {
                    return BuilderAction.cancelReload;
                }
            }
        },
    });

    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderButton action="'testCancelReload'">Click</BuilderButton>`;
        }
    );

    await setupHTMLBuilder(`<div class="test-options-target">Target</div>`);
    await contains(":iframe .test-options-target").click();
    await contains(".options-container [data-action-id='testCancelReload']").click();
    expect(".o_blockUI").toHaveCount(0);
    expect.verifySteps([]);

    const editingEl = queryOne(":iframe .test-options-target");
    editingEl.classList.add("should_reload");
    await contains(":iframe .test-options-target").click();
    await contains(".options-container [data-action-id='testCancelReload']").click();
    expect(".o_blockUI").toHaveCount(1);
    resolve();
    await animationFrame();
    expect(".o_blockUI").toHaveCount(0);
    expect.verifySteps(["save"]);
});

test("UI is unblocked when getting an error on a reloadable operation", async () => {
    expect.errors(1);
    const { promise, resolve } = Promise.withResolvers();
    addBuilderAction({
        TestAction: class extends BuilderAction {
            static id = "testAction";
            setup() {
                this.reload = {};
            }
            async apply({ editingElement }) {
                await promise;
                throw new Error("Apply failed!");
            }
        },
    });

    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderButton action="'testAction'">Click</BuilderButton>`;
        }
    );
    const { waitSidebarUpdated } = await setupHTMLBuilder(
        `<div class="test-options-target">Target</div>`
    );
    await contains(":iframe .test-options-target").click();
    await contains(".options-container [data-action-id='testAction']").click();
    expect(".o_blockUI").toHaveCount(1);
    resolve();
    await waitSidebarUpdated();
    expect(".o_blockUI").toHaveCount(0);
    expect.verifyErrors(["Apply failed!"]);
});
