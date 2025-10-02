import {
    addBuilderOption,
    addBuilderAction,
    setupHTMLBuilder,
    getSnippetStructure,
} from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { ClassAction } from "@html_builder/core/core_builder_action_plugin";
import { Operation } from "@html_builder/core/operation";
import { HistoryPlugin } from "@html_editor/core/history_plugin";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { advanceTime, Deferred, delay, hover, press, tick } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

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
        addBuilderOption({
            selector: ".test-options-target",
            template: xml`<BuilderButton action="'customAction'"/>`,
        });
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
        addBuilderOption({
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
        addBuilderOption({
            selector: ".test-options-target",
            template: xml`<BuilderRow>
                <BuilderColorPicker enabledTabs="['solid']" styleAction="'background-color'" action="'customAction'"/>
            </BuilderRow>`,
        });

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
        addBuilderOption({
            selector: ".test-options-target",
            template: xml`
                <BuilderButton action="'testAction'"/>
                <BuilderButton classAction="'test'"/>`,
        });
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        await contains("[data-action-id='testAction']").hover();
        await contains("[data-class-action='test']").click();
        expect(":iframe .test-options-target").toHaveOuterHTML(
            '<div class="test-options-target o-paragraph test">b</div>'
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
        addBuilderOption({
            selector: ".test-options-target",
            template: xml`
                <BuilderButton action="'testAction'"/>
                <BuilderButton classAction="'test'"/>`,
        });
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        await contains("[data-action-id='testAction']").click();
        await contains("[data-class-action='test']").click();
        expect(":iframe .test-options-target").toHaveOuterHTML(
            '<div class="test-options-target o-paragraph test">b</div>'
        );
        // preview + commit
        expect.verifyErrors(["This action should crash", "This action should crash"]);
    });

    test("Error in apply() on outdated snippet shows warning notification", async () => {
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
        addBuilderOption({
            selector: ".s_title",
            template: xml`<BuilderButton action="'testAction'"/>`,
        });
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
        await contains("[data-action-id='testAction']").click();
        //The preview and the apply should crash on the click.
        expect(".o_notification .o_notification_bar.bg-warning").toHaveCount(2);
        expect(".o_notification_content").toHaveText(
            "Outdated Snippet. This snippet is outdated. Please drag a new version from the snippet panel to update it."
        );
    });

    test("Error in load() on outdated snippet shows warning notification", async () => {
        class TestAction extends BuilderAction {
            static id = "testAction";
            load() {
                throw new Error("Load failed");
            }
            apply({ editingElement }) {
                editingElement.classList.add("success");
            }
        }
        addBuilderAction({
            TestAction,
        });
        addBuilderOption({
            selector: ".s_title",
            template: xml`<BuilderButton action="'testAction'"/>`,
        });
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
        await contains("[data-action-id='testAction']").click();
        // Two notifications: one for preview load, one for commit load
        expect(".o_notification .o_notification_bar.bg-warning").toHaveCount(2);
        expect(".o_notification_content").toHaveCount(2);
    });

    test("Error on outdated snippet inside parent element shows warning", async () => {
        class TestAction extends BuilderAction {
            static id = "testAction";
            apply({ editingElement }) {
                throw new Error("This action should crash");
            }
        }
        addBuilderAction({
            TestAction,
        });
        addBuilderOption({
            selector: ".s_title h1",
            template: xml`<BuilderButton action="'testAction'"/>`,
        });
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
        await contains(":iframe .s_title h1").click();
        await contains("[data-action-id='testAction']").click();
        // Two notifications: one for preview, one for commit
        expect(".o_notification .o_notification_bar.bg-warning").toHaveCount(2);
        expect(".o_notification_content").toHaveCount(2);
    });

    test("Error in apply() on up-to-date snippet propagates normally", async () => {
        expect.errors(2); // preview + commit
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
        addBuilderOption({
            selector: ".s_title",
            template: xml`<BuilderButton action="'testAction'"/>`,
        });
        await setupHTMLBuilder(
            `<section class="s_title" data-snippet="s_title" data-vcss="001" data-name="Title">
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
        await contains("[data-action-id='testAction']").click();
        expect(".o_notification").toHaveCount(0);
        await tick();
        expect.verifyErrors(["This action should crash", "This action should crash"]);
    });

    test("Error in load() on up-to-date snippet propagates normally", async () => {
        expect.errors(2);
        class TestAction extends BuilderAction {
            static id = "testAction";
            load() {
                throw new Error("Load failed (testing)");
            }
            apply({ editingElement }) {
                editingElement.classList.add("success");
            }
        }
        addBuilderAction({
            TestAction,
        });
        addBuilderOption({
            selector: ".s_title",
            template: xml`<BuilderButton action="'testAction'"/>`,
        });
        await setupHTMLBuilder(
            `<section class="s_title" data-snippet="s_title" data-vcss="001" data-name="Title">
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
        await contains("[data-action-id='testAction']").click();
        expect.verifyErrors(["Load failed (testing)", "Load failed (testing)"]);
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
        addBuilderOption({
            selector: ".s_title",
            template: xml`<BuilderNumberInput action="'testAction'"/>`,
        });

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
            "Outdated Snippet. This snippet is outdated. Please drag a new version from the snippet panel to update it."
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
        addBuilderOption({
            selector: ".s_title",
            template: xml`<BuilderButton action="'testAction'"/>`,
        });

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
            "Outdated Snippet. This snippet is outdated. Please drag a new version from the snippet panel to update it."
        );
    });

    test("Error in clean() on outdated snippet shows warning notification", async () => {
        class TestAction extends BuilderAction {
            static id = "testAction";
            isApplied({ editingElement }) {
                return editingElement.classList.contains("applied");
            }
            clean({ editingElement }) {
                throw new Error("Clean should crash");
            }
            apply({ editingElement }) {
                editingElement.classList.add("applied");
            }
        }
        addBuilderAction({
            TestAction,
        });
        addBuilderOption({
            selector: ".s_title",
            template: xml`<BuilderButton action="'testAction'"/>`,
        });

        await setupHTMLBuilder(
            `<section class="s_title applied" data-snippet="s_title" data-name="Title">
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
        // Click the button to trigger clean (since it's already applied)
        await contains("[data-action-id='testAction']").click();
        // A warning notification should be shown
        expect(".o_notification .o_notification_bar.bg-warning").toHaveCount(2);
        expect(".o_notification_content").toHaveText(
            "Outdated Snippet. This snippet is outdated. Please drag a new version from the snippet panel to update it."
        );
    });

    test("Error in clean() on up-to-date snippet propagates normally", async () => {
        expect.errors(2); // preview + commit
        class TestAction extends BuilderAction {
            static id = "testAction";
            isApplied({ editingElement }) {
                return editingElement.classList.contains("applied");
            }
            clean({ editingElement }) {
                throw new Error("Clean should crash");
            }
            apply({ editingElement }) {
                editingElement.classList.add("applied");
            }
        }
        addBuilderAction({
            TestAction,
        });
        addBuilderOption({
            selector: ".s_title",
            template: xml`<BuilderButton action="'testAction'"/>`,
        });

        await setupHTMLBuilder(
            `<section class="s_title applied" data-snippet="s_title" data-vcss="001" data-name="Title">
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
        await contains("[data-action-id='testAction']").click();
        expect(".o_notification").toHaveCount(0);
        expect.verifyErrors(["Clean should crash", "Clean should crash"]);
    });

    test("Error in clean() via cleanSelectedItem on outdated snippet shows warning", async () => {
        class TestAction extends ClassAction {
            static id = "testAction";
            clean({ editingElement }) {
                throw new Error("Clean via cleanSelectedItem should crash");
            }
        }
        addBuilderAction({
            TestAction,
        });
        addBuilderOption({
            selector: ".s_title",
            template: xml`
            <BuilderButtonGroup action="'testAction'">
                <BuilderButton actionParam="'class1'">1</BuilderButton>
                <BuilderButton actionParam="'class2'">2</BuilderButton>
            </BuilderButtonGroup>`,
        });

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
        await contains("[data-action-param='class2']").click();
        expect(".o_notification .o_notification_bar.bg-warning").toHaveCount(2); // preview + commit
        expect(".o_notification_content").toHaveText(
            "Outdated Snippet. This snippet is outdated. Please drag a new version from the snippet panel to update it."
        );
    });
});
