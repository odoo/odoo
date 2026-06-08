import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
    editBuilderRangeValue,
} from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { HistoryPlugin } from "@html_editor/core/history_plugin";
import { expect, test, describe } from "@odoo/hoot";
import { advanceTime, animationFrame, click, edit, fill, freezeTime, press } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";

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
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderRange action="'customAction'"/>`,
    });
    await setupHTMLBuilder(`
        <div class="test-options-target">10</div>
    `);
    await contains(":iframe .test-options-target").click();
    await editBuilderRangeValue(".options-container input", "50");

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
            apply({ editingElement, value, isPreviewing }) {
                if (!isPreviewing) {
                    expect.step(`customAction ${value}`);
                }
                editingElement.textContent = value;
            }
        },
    });
    addBuilderOption({
        selector: ".test-integer-step",
        template: xml`<BuilderRange action="'customAction'" step="2"/>`,
    });
    addBuilderOption({
        selector: ".test-fractional-step",
        template: xml`<BuilderRange action="'customAction'" step="0.15"/>`,
    });
    await setupHTMLBuilder(`
        <div class="test-integer-step">10</div>
        <div class="test-fractional-step">14.85</div>
    `);

    freezeTime();

    // Test integer steps
    await contains(":iframe .test-integer-step").click();
    // Simulate ArrowUp
    await contains(".options-container input").press("ArrowUp");
    await advanceTime(750);
    expect(":iframe .test-integer-step").toHaveInnerHTML("12");
    // Simulate ArrowRight
    await contains(".options-container input").press("ArrowRight");
    await advanceTime(750);
    expect(":iframe .test-integer-step").toHaveInnerHTML("14");
    // Simulate ArrowDown
    await contains(".options-container input").press("ArrowDown");
    await advanceTime(750);
    expect(":iframe .test-integer-step").toHaveInnerHTML("12");
    // Simulate ArrowLeft
    await contains(".options-container input").press("ArrowLeft");
    await advanceTime(750);
    expect(":iframe .test-integer-step").toHaveInnerHTML("10");
    // Verify steps
    expect.verifySteps([
        "customAction 12",
        "customAction 14",
        "customAction 12",
        "customAction 10",
    ]);

    // Test fractional steps
    await contains(":iframe .test-fractional-step").click();
    // Simulate ArrowUp
    await contains(".options-container input").press("ArrowUp");
    await advanceTime(750);
    expect(":iframe .test-fractional-step").toHaveInnerHTML("15");
    // Simulate ArrowRight
    await contains(".options-container input").press("ArrowRight");
    await advanceTime(750);
    expect(":iframe .test-fractional-step").toHaveInnerHTML("15.15");
    // Simulate ArrowDown
    await contains(".options-container input").press("ArrowDown");
    await advanceTime(750);
    expect(":iframe .test-fractional-step").toHaveInnerHTML("15");
    // Simulate ArrowLeft
    await contains(".options-container input").press("ArrowLeft");
    await advanceTime(750);
    expect(":iframe .test-fractional-step").toHaveInnerHTML("14.85");
    // Verify steps
    expect.verifySteps([
        "customAction 15",
        "customAction 15.15",
        "customAction 15",
        "customAction 14.85",
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
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderRange action="'customAction'" step="2"/>`,
    });
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
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderRange withNumberInput="true" action="'customAction'"/>`,
    });
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
    await expect.verifySteps(["customAction isPreviewing: false"]);
    await expect(".options-container input[type='number']").toHaveProperty("value", 10);
});

test("number input should have the same min, max and step as the range input", async () => {
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
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderRange withNumberInput="true" action="'customAction'" min="0" max="5" step="2"/>`,
    });
    await setupHTMLBuilder(`
        <div class="test-options-target">2</div>
    `);

    await contains(":iframe .test-options-target").click();
    await contains(".options-container input[type='number']").keyDown("ArrowUp");

    // Check that step=2
    expect(".options-container input[type='number']").toHaveProperty("value", 4);
    expect(":iframe .test-options-target").toHaveInnerHTML("4");
    expect.verifySteps(["customAction 4"]);

    await contains(".options-container input[type='number']").keyDown("ArrowUp");

    // Check that max=5
    expect(".options-container input[type='number']").toHaveProperty("value", 5);
    expect(":iframe .test-options-target").toHaveInnerHTML("5");
    expect.verifySteps(["customAction 5"]);

    await contains(".options-container input[type='number']").keyDown("ArrowDown");
    await contains(".options-container input[type='number']").keyDown("ArrowDown");
    await contains(".options-container input[type='number']").keyDown("ArrowDown");

    // Check that min=0
    expect(".options-container input[type='number']").toHaveProperty("value", 0);
    expect(":iframe .test-options-target").toHaveInnerHTML("0");
    expect.verifySteps(["customAction 3", "customAction 1", "customAction 0"]);
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
        addBuilderOption({
            selector: ".test-options-target",
            template: xml`<BuilderRange action="'customAction'" unit="'px'"/>`,
        });
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
        addBuilderOption({
            selector: ".test-options-target",
            template: xml`<BuilderRange action="'customAction'" unit="'s'" saveUnit="'ms'"/>`,
        });
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
        addBuilderOption({
            selector: ".test-options-target",
            template: xml`<BuilderRange action="'customAction'" unit="'s'" saveUnit="'ms'"/>`,
        });
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
        addBuilderOption({
            selector: ".test-options-target",
            template: xml`<BuilderRange action="'customAction'" unit="'px'" saveUnit="''"/>`,
        });
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
        addBuilderOption({
            selector: ".test-options-target",
            template: xml`<BuilderRange action="'customAction'" unit="'s'" saveUnit="'ms'"/>`,
        });
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

test("should map range from 0 to 100 scale when empty convertorRatio object is passed", async () => {
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            getValue({ editingElement }) {
                return editingElement.textContent;
            }
            apply({ editingElement, value }) {
                expect.step(`applied ${value}`);
                editingElement.textContent = value;
            }
        },
    });
    addBuilderOption({
        selector: ".test-ratio-target",
        template: xml`<BuilderRange action="'customAction'" min="-2" max="2" withNumberInput="true" convertorRatio="{}" step="0.1"/>`,
    });
    await setupHTMLBuilder(`<div class="test-ratio-target">-2</div>`);
    await contains(":iframe .test-ratio-target").click();
    expect(".options-container input[type='number']").toHaveProperty("value", 1);
    // Arrow down at min (-2) stays at -2 (boundary check)
    await contains(".options-container input[type='range']").focus();
    await press("ArrowDown");
    await advanceTime(750);
    expect.verifySteps(["applied -2", "applied -2"]);
    // Arrow up on slider: moves from 0 -> 2.5 (ratio), applies -1.9
    // Ratioed step: (0.1 / 4) * 100 = 2.5 per arrow press
    await press("ArrowUp");
    await advanceTime(750);
    expect.verifySteps(["applied -1.9", "applied -1.9"]);
    expect(".options-container input[type='number']").toHaveProperty("value", 3);
    // Arrow up on input: moves from 2.5 -> 5 (ratio), applies -1.8
    await contains(".options-container input[type='number']").focus();
    await press("ArrowUp");
    await advanceTime(750);
    // Since the values are not committed when pressing the up/down arrow keys,
    // we expect the change to be applied only once which is preview operation.
    expect.verifySteps(["applied -1.84"]);
    expect(".options-container input[type='number']").toHaveProperty("value", 5);
});
