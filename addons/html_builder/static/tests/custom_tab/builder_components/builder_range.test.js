import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { HistoryPlugin } from "@html_editor/core/history_plugin";
import { expect, test, describe } from "@odoo/hoot";
import {
    advanceTime,
    animationFrame,
    click,
    edit,
    fill,
    freezeTime,
    press,
    waitFor,
} from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { delay } from "@web/core/utils/concurrency";
import { BaseOptionComponent } from "@html_builder/core/utils";

describe.current.tags("desktop");

test("should commit changes", async () => {
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            getValue({ editingElement }) {
                return editingElement.innerHTML;
            }
            apply({ editingElement, value }) {
                expect.step(`customAction ${value}`);
                editingElement.innerHTML = value;
            }
        },
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderRange action="'customAction'" displayRangeValue="true"/>`;
        }
    );
    await setupHTMLBuilder(`
        <div class="test-options-target">10</div>
    `);
    await contains(":iframe .test-options-target").click();

    const input = await waitFor(".options-container input");
    input.value = 50;
    input.dispatchEvent(new Event("input"));
    await delay();
    input.dispatchEvent(new Event("change"));
    await delay();

    expect.verifySteps(["customAction 50", "customAction 50"]);
    expect(":iframe .test-options-target").toHaveInnerHTML("50");
    await click(document.body);
    await animationFrame();
    expect(".o-snippets-top-actions .fa-undo").toBeEnabled();
    expect(".o-snippets-top-actions .fa-repeat").not.toBeEnabled();
});

test("range input should step up or down with arrow keys", async () => {
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            getValue({ editingElement }) {
                return editingElement.textContent;
            }
            apply({ editingElement, value }) {
                expect.step(`customAction ${value}`);
                editingElement.textContent = value;
            }
        },
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderRange action="'customAction'" step="2" displayRangeValue="true"/>`;
        }
    );
    await setupHTMLBuilder(`
        <div class="test-options-target">10</div>
    `);
    await contains(":iframe .test-options-target").click();
    // Simulate ArrowUp
    await contains(".options-container input").keyDown("ArrowUp");
    expect(":iframe .test-options-target").toHaveInnerHTML("12");
    // Simulate ArrowRight
    await contains(".options-container input").keyDown("ArrowRight");
    expect(":iframe .test-options-target").toHaveInnerHTML("14");
    // Simulate ArrowDown
    await contains(".options-container input").keyDown("ArrowDown");
    expect(":iframe .test-options-target").toHaveInnerHTML("12");
    // Simulate ArrowLeft
    await contains(".options-container input").keyDown("ArrowLeft");
    expect(":iframe .test-options-target").toHaveInnerHTML("10");

    expect.verifySteps([
        "customAction 12",
        "customAction 14",
        "customAction 12",
        "customAction 10",
    ]);
});

test("keeping an arrow key pressed should commit only once", async () => {
    patchWithCleanup(HistoryPlugin.prototype, {
        makePreviewableAsyncOperation(...args) {
            const res = super.makePreviewableAsyncOperation(...args);
            const commit = res.commit;
            res.commit = async (...args) => {
                expect.step(`commit ${args[0][0].actionValue}`);
                commit(...args);
            };
            return res;
        },
    });
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            getValue({ editingElement }) {
                return editingElement.textContent;
            }
            apply({ editingElement, value }) {
                expect.step(`customAction ${value}`);
                editingElement.textContent = value;
            }
        },
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderRange action="'customAction'" step="2" displayRangeValue="true"/>`;
        }
    );
    freezeTime();
    await setupHTMLBuilder(`
        <div class="test-options-target">10</div>
    `);
    await contains(":iframe .test-options-target").click();
    // Simulate a long press on ArrowUp
    await contains(".options-container input").keyDown("ArrowUp");
    await advanceTime(500);
    await contains(".options-container input").keyDown("ArrowUp");
    await advanceTime(50);
    await contains(".options-container input").keyDown("ArrowUp");
    await advanceTime(50);
    await contains(".options-container input").keyDown("ArrowUp");
    expect(":iframe .test-options-target").toHaveInnerHTML("18");
    expect.verifySteps([
        "customAction 12",
        "customAction 14",
        "customAction 16",
        "customAction 18",
    ]);
    await advanceTime(550);
    expect.verifySteps(["commit 18", "customAction 18"]);
});

test("should syncronize previews", async () => {
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            getValue({ editingElement }) {
                return editingElement.textContent;
            }
            apply({ editingElement, value, isPreviewing }) {
                expect.step(`customAction isPreviewing: ${isPreviewing}`);
                editingElement.textContent = value;
            }
        },
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderRange withNumberInput="true" action="'customAction'"/>`;
        }
    );
    await setupHTMLBuilder(`
        <div class="test-options-target">10</div>
    `);
    // Change the value using the number input.
    // Fill without pressing Enter will trigger a preview.
    await contains(":iframe .test-options-target").click();
    await contains(".options-container input[type='number']").click();
    await edit("9");
    await animationFrame();
    expect.verifySteps(["customAction isPreviewing: true", "customAction isPreviewing: true"]);
    // Verify that the slider value is updated during preview
    await animationFrame();
    await expect(".options-container input[type='range']").toHaveValue(9);
    expect.verifySteps([]);

    // Click somewhere to commit the change
    await contains(":iframe .test-options-target").click();
    expect.verifySteps(["customAction isPreviewing: false"]);
    await expect(".options-container input[type='range']").toHaveValue(9);

    // Change the value using the slider input.
    // Pressing arrow key will trigger a preview.
    await contains(":iframe .test-options-target").click();
    await contains(".options-container input[type='range']").click();
    await press("ArrowUp");
    expect.verifySteps(["customAction isPreviewing: true"]);

    // Verify that the number input value is updated during preview
    await animationFrame();
    await expect(".options-container input[type='number']").toHaveProperty("value", 10);
    expect.verifySteps([]);

    // Slider changes are committed automatically after a short delay
    await advanceTime(1200);
    await expect.verifySteps([
        "customAction isPreviewing: false",
        "customAction isPreviewing: false",
    ]);
    await expect(".options-container input[type='number']").toHaveProperty("value", 10);
});

describe("unit & saveUnit", () => {
    test("should handle unit", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.textContent;
                }
                apply({ editingElement, value }) {
                    expect.step(`customAction ${value}`);
                    editingElement.textContent = value;
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderRange action="'customAction'" unit="'px'"/>`;
            }
        );
        await setupHTMLBuilder(`
                    <div class="test-options-target">5px</div>
                `);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        await click(".options-container input");
        expect(".options-container input").toHaveValue(5);
        await press("ArrowRight");
        expect.verifySteps(["customAction 6px"]);
        expect(":iframe .test-options-target").toHaveInnerHTML("6px");
    });
    test("should handle saveUnit", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.textContent;
                }
                apply({ editingElement, value }) {
                    expect.step(`customAction ${value}`);
                    editingElement.textContent = value;
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderRange action="'customAction'" unit="'s'" saveUnit="'ms'"/>`;
            }
        );
        await setupHTMLBuilder(`
                    <div class="test-options-target">5000ms</div>
                `);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        await click(".options-container input");
        expect(".options-container input").toHaveValue(5);
        await fill("7");
        await animationFrame();
        expect.verifySteps(["customAction 7000ms"]);
        expect(":iframe .test-options-target").toHaveInnerHTML("7000ms");
    });
    test("should handle saveUnit even without explicit unit", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.textContent;
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderRange action="'customAction'" unit="'s'" saveUnit="'ms'"/>`;
            }
        );
        // note that 5000 has no unit of measure
        await setupHTMLBuilder(`
                    <div class="test-options-target">5000</div>
                `);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        await click(".options-container input");
        expect(".options-container input").toHaveValue(5);
    });
    test("should handle empty saveUnit", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.textContent;
                }
                apply({ editingElement, value }) {
                    expect.step(`customAction ${value}`);
                    editingElement.textContent = value;
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderRange action="'customAction'" unit="'px'" saveUnit="''"/>`;
            }
        );
        await setupHTMLBuilder(`
                    <div class="test-options-target">5</div>
                `);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        await click(".options-container input");
        expect(".options-container input").toHaveValue(5);
        await fill(15);
        await animationFrame();
        expect.verifySteps(["customAction 15"]);
        expect(":iframe .test-options-target").toHaveInnerHTML("15");
    });
    test("should handle savedUnit", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.textContent;
                }
                apply({ editingElement, value }) {
                    expect.step(`customAction ${value}`);
                    editingElement.textContent = value;
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderRange action="'customAction'" unit="'s'" saveUnit="'ms'"/>`;
            }
        );
        await setupHTMLBuilder(`
                    <div class="test-options-target">5s</div>
                `);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        await click(".options-container input");
        expect(".options-container input").toHaveValue(5);
        await fill("7");
        await animationFrame();
        expect.verifySteps(["customAction 7000ms"]);
        expect(":iframe .test-options-target").toHaveInnerHTML("7000ms");
    });
});
