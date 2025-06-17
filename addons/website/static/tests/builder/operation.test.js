import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { advanceTime, Deferred, delay, hover, press, tick } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { Operation } from "@html_builder/core/operation";
import { HistoryPlugin } from "@html_editor/core/history_plugin";
import {
    addActionOption,
    addOption,
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "./website_helpers";
import { BuilderAction } from "@html_builder/core/builder_action";

describe("Operation", () => {
    test("handle 3 concurrent cancellable operations (with delay)", async () => {
        const operation = new Operation();
        function makeCall(data) {
            let resolve;
            const promise = new Promise((r) => {
                resolve = r;
            });
            async function load() {
                expect.step(`load before ${data}`);
                await promise;
                expect.step(`load after ${data}`);
            }
            function apply() {
                expect.step(`apply ${data}`);
            }

            operation.next(apply, { load, cancellable: true });
            return {
                resolve,
            };
        }
        const call1 = makeCall(1);
        await delay();
        const call2 = makeCall(2);
        await delay();
        const call3 = makeCall(3);
        await delay();
        call1.resolve();
        call2.resolve();
        call3.resolve();
        await operation.mutex.getUnlockedDef();
        expect.verifySteps([
            //
            "load before 1",
            "load after 1",
            "load before 3",
            "load after 3",
            "apply 3",
        ]);
    });
    test("handle 3 concurrent cancellable operations (without delay)", async () => {
        const operation = new Operation();
        function makeCall(data) {
            let resolve;
            const promise = new Promise((r) => {
                resolve = r;
            });
            async function load() {
                expect.step(`load before ${data}`);
                await promise;
                expect.step(`load after ${data}`);
            }
            function apply() {
                expect.step(`apply ${data}`);
            }

            operation.next(apply, { load, cancellable: true });
            return {
                resolve,
            };
        }
        const call1 = makeCall(1);
        const call2 = makeCall(2);
        const call3 = makeCall(3);
        call1.resolve();
        call2.resolve();
        call3.resolve();
        await operation.mutex.getUnlockedDef();
        expect.verifySteps(["load before 3", "load after 3", "apply 3"]);
    });
});

describe("Block editable", () => {
    defineWebsiteModels();

    test("Doing an operation should block the editable during its execution", async () => {
        const customActionDef = new Deferred();
        addActionOption({
            customAction: class extends BuilderAction {
                static id = "customAction";
                load() {
                    return customActionDef;
                }
                apply({ editingElement }) {
                    editingElement.classList.add("custom-action");
                }
            },
        });
        addOption({
            selector: ".test-options-target",
            template: xml`<BuilderButton action="'customAction'"/>`,
        });
        await setupWebsiteBuilder(`<div class="test-options-target">TEST</div>`, {
            loadIframeBundles: true,
        });

        await contains(":iframe .test-options-target").click();
        await contains("[data-action-id='customAction']").click();
        expect(":iframe .o_loading_screen:not(.o_we_ui_loading)").toHaveCount(1);
        await new Promise((resolve) => setTimeout(resolve, 600));
        expect(":iframe .o_loading_screen.o_we_ui_loading").toHaveCount(1);

        customActionDef.resolve();
        await tick();
        expect(":iframe .o_loading_screen.o_we_ui_loading").toHaveCount(0);
        expect(":iframe .test-options-target").toHaveClass("custom-action");
    });
});

describe("Async operations", () => {
    defineWebsiteModels();
    beforeEach(() => {
        patchWithCleanup(HistoryPlugin.prototype, {
            makePreviewableAsyncOperation(operation) {
                const res = super.makePreviewableAsyncOperation(operation);
                const revert = res.revert;
                res.revert = async () => {
                    await revert();
                    expect.step("revert");
                };
                return res;
            },
        });
    });

    test("In clickable component, revert is awaited before applying the next apply", async () => {
        const applyDelay = 1000;
        addActionOption({
            customAction: class extends BuilderAction {
                static id = "customAction";
                async apply({ editingElement, value }) {
                    await new Promise((resolve) => setTimeout(resolve, applyDelay));
                    editingElement.classList.add(value);
                    expect.step("apply first");
                }
            },
            customAction2: class extends BuilderAction {
                static id = "customAction2";
                apply({ editingElement, value }) {
                    editingElement.classList.add(value);
                    expect.step("apply second");
                }
            },
        });
        addOption({
            selector: ".test-options-target",
            template: xml`
                <BuilderRow label.translate="Type">
                    <BuilderSelect>
                        <BuilderSelectItem action="'customAction'" actionValue="'first'">first</BuilderSelectItem>
                        <BuilderSelectItem action="'customAction2'" actionValue="'second'">second</BuilderSelectItem>
                    </BuilderSelect>
                </BuilderRow>
            `,
        });

        await setupWebsiteBuilder(`<div class="test-options-target">TEST</div>`);
        await contains(":iframe .test-options-target").click();
        await contains(".options-container [data-label='Type'] .btn-secondary ").click();
        await hover(".popover [data-action-value='first']");
        await hover(".popover [data-action-value='second']");
        await advanceTime(applyDelay + 50);
        expect.verifySteps(["apply first", "revert", "apply second"]);
        expect(":iframe .test-options-target").toHaveClass("second");
        expect(":iframe .test-options-target").not.toHaveClass("first");
        // Escape the select to trigger an explicit revert. Otherwise, the test
        // sometimes fails with an unverified step.
        await press(["Escape"]);
        expect.verifySteps(["revert"]);
    });

    test("In ColorPicker, revert is awaited before applying the next apply", async () => {
        const applyDelay = 1000;
        addActionOption({
            customAction: class extends BuilderAction {
                static id = "customAction";
                async apply({ editingElement }) {
                    let color =
                        getComputedStyle(editingElement).getPropertyValue("background-color");
                    if (color === "rgb(255, 0, 0)") {
                        color = "red";
                        await new Promise((resolve) => setTimeout(resolve, applyDelay));
                    } else {
                        color = "blue";
                    }
                    editingElement.classList.add(color);
                    expect.step(`apply ${color}`);
                }
            },
        });
        addOption({
            selector: ".test-options-target",
            template: xml`<BuilderRow>
                <BuilderColorPicker enabledTabs="['solid']" styleAction="'background-color'" action="'customAction'"/>
            </BuilderRow>`,
        });

        await setupWebsiteBuilder(`<div class="test-options-target">TEST</div>`);
        await contains(":iframe .test-options-target").click();

        await contains(".we-bg-options-container .o_we_color_preview").click();
        await contains(".o-overlay-item [data-color='#FF0000']").hover();
        await contains(".o-overlay-item [data-color='#0000FF']").hover();
        await advanceTime(applyDelay + 50);
        expect(":iframe .test-options-target").toHaveClass("blue");
        expect(":iframe .test-options-target").not.toHaveClass("red");
        expect.verifySteps(["apply red", "revert", "apply blue"]);
        // Escape the colorpicker to trigger an explicit revert. Otherwise, the
        // test sometimes fails with an unverified step.
        await press(["Escape"]);
        expect.verifySteps(["revert"]);
    });
});
