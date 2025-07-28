import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { HistoryPlugin } from "@html_editor/core/history_plugin";
import { expect, test, describe } from "@odoo/hoot";
import { advanceTime, animationFrame, click, freezeTime, waitFor } from "@odoo/hoot-dom";
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
