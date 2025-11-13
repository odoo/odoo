import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, Deferred, delay } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";

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
