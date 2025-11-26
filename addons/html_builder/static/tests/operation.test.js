import {
    addBuilderOption,
    addBuilderAction,
    setupHTMLBuilder,
    getSnippetStructure,
} from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { ClassAction } from "@html_builder/core/core_builder_action_plugin";
import { Operation } from "@html_builder/core/operation";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { HistoryPlugin } from "@html_editor/core/history_plugin";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { advanceTime, animationFrame, Deferred, delay, hover, press, tick } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

describe("OperationMutex", () => {
    test("skips queued actions until emptied after clearQueue", async () => {
        const operation = new Operation();
        const { mutex } = operation;
        const firstStarted = Promise.withResolvers();
        const firstDone = Promise.withResolvers();

        mutex.exec(async () => {
            expect.step("first start");
            firstStarted.resolve();
            await firstDone.promise;
            expect.step("first done");
        });

        await firstStarted.promise;
        mutex.clearQueue();
        mutex.exec(() => {
            expect.step("skip 1");
        });
        mutex.exec(() => {
            expect.step("skip 2");
        });

        firstDone.resolve();
        await mutex.getUnlockedDef();

        await mutex.exec(() => {
            expect.step("after clear");
        });

        expect.verifySteps(["first start", "first done", "after clear"]);
    });
});

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

describe("Block editable", () => {
    test("Doing an operation should block the editable during its execution", async () => {
        const customActionDef = new Deferred();
        addBuilderAction({
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
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderButton action="'customAction'"/>`;
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target">TEST</div>`, {
            loadIframeBundles: true,
        });

        await contains(":iframe .test-options-target").click();
        await contains("[data-action-id='customAction']").click();
        expect(":iframe .o_loading_screen:not(.o_we_ui_loading)").toHaveCount(1);
        await advanceTime(50); // cancelTime=50 trigger by the preview
        await advanceTime(500); // setTimeout in addLoadingElement
        expect(":iframe .o_loading_screen.o_we_ui_loading").toHaveCount(1);

        customActionDef.resolve();
        await tick();
        expect(":iframe .o_loading_screen.o_we_ui_loading").toHaveCount(0);
        expect(":iframe .test-options-target").toHaveClass("custom-action");
    });
});

describe("Async operations", () => {
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
        addBuilderAction({
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
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`
                    <BuilderRow label.translate="Type">
                        <BuilderSelect>
                            <BuilderSelectItem action="'customAction'" actionValue="'first'">first</BuilderSelectItem>
                            <BuilderSelectItem action="'customAction2'" actionValue="'second'">second</BuilderSelectItem>
                        </BuilderSelect>
                    </BuilderRow>
                `;
            }
        );

        await setupHTMLBuilder(`<div class="test-options-target">TEST</div>`);
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
        addBuilderAction({
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
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderRow>
                    <BuilderColorPicker enabledTabs="['solid']" styleAction="'background-color'" action="'customAction'"/>
                </BuilderRow>`;
            }
        );

        await setupHTMLBuilder(`<div class="test-options-target">TEST</div>`);
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

describe("Operation that will fail", () => {
    test("html builder must not be blocked if a preview crashes", async () => {
        expect.errors(1);
        class TestAction extends BuilderAction {
            static id = "testAction";
            apply({ editingElement }) {
                editingElement.classList.add("fail");
                throw new Error("This action should crash");
            }
        }
        addBuilderAction({
            TestAction,
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`
                    <BuilderButton action="'testAction'"/>
                    <BuilderButton classAction="'test'"/>`;
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        await contains("[data-action-id='testAction']").hover();
        await contains("[data-class-action='test']").click();
        expect(":iframe .test-options-target").toHaveOuterHTML(
            '<div class="test-options-target test">b</div>'
        );
        expect.verifyErrors(["This action should crash"]);
    });

    test("html builder must not be blocked when a failed action is commit", async () => {
        expect.errors(2);
        class TestAction extends BuilderAction {
            static id = "testAction";
            apply({ editingElement }) {
                editingElement.classList.add("fail");
                throw new Error("This action should crash");
            }
        }
        addBuilderAction({
            TestAction,
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`
                    <BuilderButton action="'testAction'"/>
                    <BuilderButton classAction="'test'"/>`;
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        await contains("[data-action-id='testAction']").click();
        await contains("[data-class-action='test']").click();
        expect(":iframe .test-options-target").toHaveOuterHTML(
            '<div class="test-options-target test">b</div>'
        );
        // preview + commit
        expect.verifyErrors(["This action should crash", "This action should crash"]);
    });

    test("Error in apply() on outdated snippet shows warning notification", async () => {
        expect.errors(1);
        class TestAction extends BuilderAction {
            static id = "testAction";
            apply({ editingElement }) {
                editingElement.classList.add("fail");
                throw new Error("Error on apply");
            }
        }
        addBuilderAction({
            TestAction,
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".s_title";
                static template = xml`<BuilderButton action="'testAction'"/>`;
            }
        );
        await setupHTMLBuilder(
            `<section class="s_title" data-snippet="s_title" data-name="Title">
                <h1>Old</h1>
            </section>
            <section class="s_title" data-snippet="s_title" data-vcss="001" data-name="Title">
                <h1>New</h1>
            </section>`,
            {
                snippets: {
                    snippet_structure: [
                        getSnippetStructure({
                            name: "Title",
                            groupName: "a",
                            content: `
                                <section class="s_title" data-snippet="s_title" data-vcss="001" data-name="Title">
                                    <h1>Title</h1>
                                </section>`,
                        }),
                    ],
                },
            }
        );

        // Interacting with an outdated snippet. We test that only one
        // notification is displayed (the one triggered by the hover), while the
        // error triggered by the click does not result in a second notification
        // because one is already open.
        await contains(":iframe .s_title h1:contains('Old')").click();
        await contains("[data-action-id='testAction']").hover();
        await animationFrame();
        await contains("[data-action-id='testAction']").click();
        expect(".o_notification .o_notification_bar.bg-warning").toHaveCount(1);
        expect(".o_notification_content").toHaveText(
            "This snippet is outdated. It might have caused problem during the editing. Please drag the new version from the snippet panel to update it."
        );
        expect.verifyErrors([]);

        // Close the notification and try to interact with an up-to-date snippet
        await contains(`.o_notification_close`).click();
        await contains(":iframe .s_title h1:contains('New')").click();
        await contains("[data-action-id='testAction']").hover();
        await animationFrame();
        expect(".o_notification").toHaveCount(0);
        expect.verifyErrors(["Error on apply"]);
    });

    test("Error in load() on outdated snippet shows warning notification", async () => {
        expect.errors(1);
        class TestAction extends BuilderAction {
            static id = "testAction";
            load() {
                throw new Error("Error on load");
            }
            apply({ editingElement }) {
                editingElement.classList.add("success");
            }
        }
        addBuilderAction({
            TestAction,
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".s_title";
                static template = xml`<BuilderButton action="'testAction'"/>`;
            }
        );
        await setupHTMLBuilder(
            `<section class="s_title" data-snippet="s_title" data-name="Title">
                <h1>Old</h1>
            </section>
            <section class="s_title" data-snippet="s_title" data-vcss="001" data-name="Title">
                <h1>New</h1>
            </section>`,
            {
                snippets: {
                    snippet_structure: [
                        getSnippetStructure({
                            name: "Title",
                            groupName: "a",
                            content: `
                                <section class="s_title" data-snippet="s_title" data-vcss="001" data-name="Title">
                                    <h1>Title</h1>
                                </section>`,
                        }),
                    ],
                },
            }
        );

        // Interacting with an outdated snippet. We test that only one
        // notification is displayed (the one triggered by the hover), while the
        // error triggered by the click does not result in a second notification
        // because one is already open.
        await contains(":iframe .s_title h1:contains('Old')").click();
        await contains("[data-action-id='testAction']").hover();
        await animationFrame();
        await contains("[data-action-id='testAction']").click();
        expect(".o_notification .o_notification_bar.bg-warning").toHaveCount(1);
        expect(".o_notification_content").toHaveText(
            "This snippet is outdated. It might have caused problem during the editing. Please drag the new version from the snippet panel to update it."
        );
        expect.verifyErrors([]);

        // Close the notification and try to interact with an up-to-date snippet
        await contains(`.o_notification_close`).click();
        await contains(":iframe .s_title h1:contains('New')").click();
        await contains("[data-action-id='testAction']").hover();
        await animationFrame();
        expect(".o_notification").toHaveCount(0);
        expect.verifyErrors(["Error on load"]);
    });

    test("Error in clean() on outdated snippet shows warning notification", async () => {
        expect.errors(1);
        class TestAction extends BuilderAction {
            static id = "testAction";
            isApplied({ editingElement }) {
                return editingElement.classList.contains("applied");
            }
            clean() {
                throw new Error("Error on clean");
            }
            apply({ editingElement }) {
                editingElement.classList.add("applied");
            }
        }
        addBuilderAction({
            TestAction,
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".s_title";
                static template = xml`<BuilderButton action="'testAction'"/>`;
            }
        );
        await setupHTMLBuilder(
            `<section class="s_title applied" data-snippet="s_title" data-name="Title">
                <h1>Old</h1>
            </section>
            <section class="s_title applied" data-snippet="s_title" data-vcss="001" data-name="Title">
                <h1>New</h1>
            </section>`,
            {
                snippets: {
                    snippet_structure: [
                        getSnippetStructure({
                            name: "Title",
                            groupName: "a",
                            content: `
                                <section class="s_title" data-snippet="s_title" data-vcss="001" data-name="Title">
                                    <h1>Title</h1>
                                </section>`,
                        }),
                    ],
                },
            }
        );

        // Interacting with an outdated snippet. We test that only one
        // notification is displayed (the one triggered by the hover), while the
        // error triggered by the click does not result in a second notification
        // because one is already open.
        await contains(":iframe .s_title h1:contains('Old')").click();
        await contains("[data-action-id='testAction']").hover();
        await animationFrame();
        await contains("[data-action-id='testAction']").click();
        expect(".o_notification .o_notification_bar.bg-warning").toHaveCount(1);
        expect(".o_notification_content").toHaveText(
            "This snippet is outdated. It might have caused problem during the editing. Please drag the new version from the snippet panel to update it."
        );
        expect.verifyErrors([]);

        // Close the notification and try to interact with an up-to-date snippet
        await contains(`.o_notification_close`).click();
        await contains(":iframe .s_title h1:contains('New')").click();
        await contains("[data-action-id='testAction']").hover();
        await animationFrame();
        expect(".o_notification").toHaveCount(0);
        expect.verifyErrors(["Error on clean"]);
    });

    test("Error in getValue() on outdated snippet shows warning notification", async () => {
        class TestAction extends BuilderAction {
            static id = "testAction";
            getValue({ editingElement }) {
                throw new Error("getValue should crash");
            }
            apply({ editingElement, value }) {
                editingElement.textContent = value;
            }
        }
        addBuilderAction({
            TestAction,
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".s_title";
                static template = xml`<BuilderNumberInput action="'testAction'"/>`;
            }
        );

        await setupHTMLBuilder(
            `<section class="s_title" data-snippet="s_title" data-name="Title">
                <h1>Title</h1>
            </section>`,
            {
                snippets: {
                    snippet_structure: [
                        getSnippetStructure({
                            name: "Title",
                            groupName: "a",
                            content: `
            <section class="s_title" data-snippet="s_title" data-vcss="001" data-name="Title">
                <h1>Title</h1>
            </section>`,
                        }),
                    ],
                },
            }
        );

        await contains(":iframe .s_title").click();
        // A warning notification should be shown
        expect(".o_notification .o_notification_bar.bg-warning").toHaveCount(1);
        expect(".o_notification_content").toHaveText(
            "This snippet is outdated. It might have caused problem during the editing. Please drag the new version from the snippet panel to update it."
        );
    });

    test("Error in isApplied() on outdated snippet shows warning notification", async () => {
        class TestAction extends BuilderAction {
            static id = "testAction";
            isApplied({ editingElement }) {
                throw new Error("isApplied should crash");
            }
            apply({ editingElement }) {
                editingElement.classList.add("applied");
            }
        }
        addBuilderAction({
            TestAction,
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".s_title";
                static template = xml`<BuilderButton action="'testAction'"/>`;
            }
        );

        await setupHTMLBuilder(
            `<section class="s_title" data-snippet="s_title" data-name="Title">
                <h1>Title</h1>
            </section>`,
            {
                snippets: {
                    snippet_structure: [
                        getSnippetStructure({
                            name: "Title",
                            groupName: "a",
                            content: `
            <section class="s_title" data-snippet="s_title" data-vcss="001" data-name="Title">
                <h1>Title</h1>
            </section>`,
                        }),
                    ],
                },
            }
        );

        await contains(":iframe .s_title").click();
        expect(".o_notification .o_notification_bar.bg-warning").toHaveCount(1);
        expect(".o_notification_content").toHaveText(
            "This snippet is outdated. It might have caused problem during the editing. Please drag the new version from the snippet panel to update it."
        );
    });

    test("Error in clean() via cleanSelectedItem on outdated snippet shows warning notification", async () => {
        class TestAction extends ClassAction {
            static id = "testAction";
            clean({ editingElement }) {
                throw new Error("Clean via cleanSelectedItem should crash");
            }
        }
        addBuilderAction({
            TestAction,
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".s_title";
                static template = xml`
                    <BuilderButtonGroup action="'testAction'">
                        <BuilderButton actionParam="'class1'">1</BuilderButton>
                        <BuilderButton actionParam="'class2'">2</BuilderButton>
                    </BuilderButtonGroup>`;
            }
        );

        await setupHTMLBuilder(
            `<section class="s_title class1" data-snippet="s_title" data-name="Title">
                <h1>Title</h1>
            </section>`,
            {
                snippets: {
                    snippet_structure: [
                        getSnippetStructure({
                            name: "Title",
                            groupName: "a",
                            content: `
            <section class="s_title" data-snippet="s_title" data-vcss="001" data-name="Title">
                <h1>Title</h1>
            </section>`,
                        }),
                    ],
                },
            }
        );

        await contains(":iframe .s_title").click();
        await contains("[data-action-param='class2']").hover();
        await animationFrame();
        expect(".o_notification .o_notification_bar.bg-warning").toHaveCount(1);
        expect(".o_notification_content").toHaveText(
            "This snippet is outdated. It might have caused problem during the editing. Please drag the new version from the snippet panel to update it."
        );
    });
});
