import { Editor } from "@html_editor/editor";
import { Plugin } from "@html_editor/plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { parseHTML } from "@html_editor/utils/html";
import { describe, expect, test } from "@odoo/hoot";
import { click, pointerDown, pointerUp, press, queryOne } from "@odoo/hoot-dom";
import { animationFrame, mockUserAgent, tick } from "@odoo/hoot-mock";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupEditor, testEditor } from "./_helpers/editor";
import { getContent, setSelection } from "./_helpers/selection";
import { addStep, deleteBackward, insertText, redo, undo } from "./_helpers/user_actions";

describe("reset", () => {
    test("should not add mutations in the current step from the normalization when calling reset", async () => {
        const TestPlugin = class extends Plugin {
            static name = "test";
            handleCommand(commandName) {
                switch (commandName) {
                    case "NORMALIZE":
                        this.editable.firstChild.setAttribute("data-test-normalize", "1");
                        break;
                }
            }
        };
        const { editor, el } = await setupEditor("<p>a</p>", {
            config: { Plugins: [...MAIN_PLUGINS, TestPlugin] },
        });
        const historyPlugin = editor.plugins.find((p) => p.constructor.name === "history");
        expect(el.firstChild.getAttribute("data-test-normalize")).toBe("1");
        expect(historyPlugin.steps.length).toBe(1);
        expect(historyPlugin.currentStep.mutations.length).toBe(0);
    });

    test.tags("desktop")("open table picker shouldn't add mutations", async () => {
        const { editor, el } = await setupEditor("<p>[]</p>");

        await insertText(editor, "/tab");
        await press("enter");
        await animationFrame();
        expect(".o-we-tablepicker").toHaveCount(1);
        expect(getContent(el)).toBe(
            `<p placeholder='Type "/" for commands' class="o-we-hint">[]</p>`
        );
        const historyPlugin = editor.plugins.find((p) => p.constructor.name === "history");
        expect(historyPlugin.currentStep.mutations.length).toBe(0);

        await click(".odoo-editor-editable p");
        await animationFrame();
        expect(".o-we-tablepicker").toHaveCount(0);
        expect(historyPlugin.currentStep.mutations.length).toBe(0);
    });
});

describe("undo", () => {
    test("should undo a backspace", async () => {
        await testEditor({
            contentBefore: "<p>ab []cd</p>",
            stepFunction: async (editor) => {
                deleteBackward(editor); // <p>ab[]cd</p>
                undo(editor); // <p>ab []cd</p>
            },
            contentAfter: "<p>ab []cd</p>",
        });
    });

    test("should undo a backspace, then do nothing on undo", async () => {
        await testEditor({
            contentBefore: "<p>ab []cd</p>",
            stepFunction: async (editor) => {
                deleteBackward(editor); // <p>ab[]cd</p>
                undo(editor); // <p>ab []cd</p>
                undo(editor); // <p>ab []cd</p> (nothing to undo)
            },
            contentAfter: "<p>ab []cd</p>",
        });
    });

    test("should discard draft mutations", async () => {
        const { el, editor } = await setupEditor(`<p>[]c</p>`);
        const p = el.querySelector("p");
        editor.shared.domInsert("a");
        editor.dispatch("ADD_STEP");
        p.prepend(document.createTextNode("b"));
        undo(editor);
        expect(getContent(el)).toBe(`<p>[]c</p>`);
        redo(editor);
        expect(getContent(el)).toBe(`<p>a[]c</p>`);
    });
});

describe("redo", () => {
    test("should undo, then redo a backspace", async () => {
        await testEditor({
            contentBefore: "<p>ab []cd</p>",
            stepFunction: async (editor) => {
                deleteBackward(editor); // <p>ab[]cd</p>
                undo(editor); // <p>ab []cd</p>
                redo(editor); // <p>ab[]cd</p>
            },
            contentAfter: "<p>ab[]cd</p>",
        });
    });

    test("should undo, then redo a backspace, then undo again to get back to the starting point", async () => {
        await testEditor({
            contentBefore: "<p>ab []cd</p>",
            stepFunction: async (editor) => {
                deleteBackward(editor); // <p>ab[]cd</p>
                undo(editor); // <p>ab []cd</p>
                redo(editor); // <p>ab[]cd</p>
                undo(editor); // <p>ab []cd</p>
            },
            contentAfter: "<p>ab []cd</p>",
        });
    });

    test("should undo, then redo a backspace, then do nothing on redo", async () => {
        await testEditor({
            contentBefore: "<p>ab []cd</p>",
            stepFunction: async (editor) => {
                deleteBackward(editor); // <p>ab[]cd</p>
                undo(editor); // <p>ab []cd</p>
                redo(editor); // <p>ab[]cd</p>
                redo(editor); // <p>ab[]cd</p> (nothing to redo)
            },
            contentAfter: "<p>ab[]cd</p>",
        });
    });

    test("should undo, then undo, then redo, then redo two backspaces, then do nothing on redo, then undo", async () => {
        await testEditor({
            contentBefore: "<p>ab []cd</p>",
            stepFunction: async (editor) => {
                deleteBackward(editor); // <p>ab[]cd</p>
                deleteBackward(editor); // <p>a[]cd</p>
                undo(editor); // <p>ab[]cd</p>
                undo(editor); // <p>ab []cd</p>
                redo(editor); // <p>ab[]cd</p>
                redo(editor); // <p>a[]cd</p>
                redo(editor); // <p>a[]cd</p> (nothing to redo)
            },
            contentAfter: "<p>a[]cd</p>",
        });
    });

    test("should 2x undo, then 2x redo, then 2x undo, then 2x redo a backspace", async () => {
        await testEditor({
            contentBefore: "<p>ab []cd</p>",
            stepFunction: async (editor) => {
                deleteBackward(editor); // <p>ab[]cd</p>
                undo(editor); // <p>ab []cd</p>
                undo(editor); // <p>ab []cd</p> (nothing to undo)
                redo(editor); // <p>ab[]cd</p>
                redo(editor); // <p>ab[]cd</p> (nothing to redo)
                undo(editor); // <p>ab []cd</p>
                undo(editor); // <p>ab []cd</p> (nothing to undo)
                redo(editor); // <p>ab[]cd</p>
                redo(editor); // <p>ab[]cd</p> (nothing to redo)
            },
            contentAfter: "<p>ab[]cd</p>",
        });
    });

    test("should type a, b, c, undo x2, d, undo x2, redo x2", async () => {
        await testEditor({
            contentBefore: "<p>[]</p>",
            stepFunction: async (editor) => {
                await insertText(editor, "a");
                await insertText(editor, "b");
                await insertText(editor, "c");
                undo(editor);
                undo(editor);
                await insertText(editor, "d");
                undo(editor);
                undo(editor);
                redo(editor);
                redo(editor);
            },
            contentAfter: "<p>ad[]</p>",
        });
    });

    test("should type a, b, c, undo x2, d, undo, redo x2", async () => {
        await testEditor({
            contentBefore: "<p>[]</p>",
            stepFunction: async (editor) => {
                await insertText(editor, "a");
                await insertText(editor, "b");
                await insertText(editor, "c");
                undo(editor);
                undo(editor);
                await insertText(editor, "d");
                undo(editor);
                redo(editor);
                redo(editor);
            },
            contentAfter: "<p>ad[]</p>",
        });
    });

    test("should discard draft mutations", async () => {
        const { el, editor } = await setupEditor(`<p>[]c</p>`);
        const p = el.querySelector("p");
        editor.shared.domInsert("a");
        editor.dispatch("ADD_STEP");
        undo(editor);
        expect(getContent(el)).toBe(`<p>[]c</p>`);
        p.prepend(document.createTextNode("b"));
        redo(editor);
        expect(getContent(el)).toBe(`<p>a[]c</p>`);
        undo(editor);
        expect(getContent(el)).toBe(`<p>[]c</p>`);
    });
});

describe("selection", () => {
    test("should stage the selection upon click", async () => {
        const { el, editor } = await setupEditor("<p>a</p>");
        const pElement = queryOne("p");
        await pointerDown(pElement);
        setSelection({
            anchorNode: pElement.firstChild,
            anchorOffset: 0,
            focusNode: pElement.firstChild,
            focusOffset: 0,
        });
        await tick();
        await pointerUp(pElement);
        await tick();
        const historyPlugin = editor.plugins.find((p) => p.constructor.name === "history");
        const nodeId = historyPlugin.nodeToIdMap.get(pElement.firstChild);
        expect(historyPlugin.currentStep.selection).toEqual({
            anchorNodeId: nodeId,
            anchorOffset: 0,
            focusNodeId: nodeId,
            focusOffset: 0,
        });
        expect(getContent(el)).toBe("<p>[]a</p>");
    });
});

describe("step", () => {
    test('should allow insertion of nested contenteditable="true"', async () => {
        await testEditor({
            contentBefore: `<div contenteditable="false"></div>`,
            stepFunction: async (editor) => {
                const editable = '<div contenteditable="true">abc</div>';
                editor.editable.querySelector("div").innerHTML = editable;
                editor.dispatch("ADD_STEP");
            },
            contentAfter: `<div contenteditable="false"><div contenteditable="true">abc</div></div>`,
        });
    });
});

describe("prevent mutationFilteredClasses to be set from history", () => {
    class TestMutationFilteredClassesPlugin extends Plugin {
        static name = "testRenderClasses";
        resources = {
            mutation_filtered_classes: ["x"],
        };
    }
    const Plugins = [...MAIN_PLUGINS, TestMutationFilteredClassesPlugin];
    test("should prevent mutationFilteredClasses to be added", async () => {
        await testEditor({
            contentBefore: `<p>a</p>`,
            stepFunction: async (editor) => {
                const p = editor.editable.querySelector("p");
                p.className = "x";
                editor.dispatch("ADD_STEP");
                const history = editor.plugins.find((p) => p.constructor.name === "history");
                expect(history.steps.length).toBe(1);
            },
            config: { Plugins: Plugins },
        });
    });

    test("should prevent mutationFilteredClasses to be added when adding 2 classes", async () => {
        await testEditor({
            contentBefore: `<p>a[]</p>`,
            stepFunction: async (editor) => {
                const p = editor.editable.querySelector("p");
                p.className = "x y";
                addStep(editor);
                undo(editor);
                redo(editor);
            },
            contentAfter: `<p class="y">a[]</p>`,
            config: { Plugins: Plugins },
        });
    });

    test("should prevent mutationFilteredClasses to be added in historyApply", async () => {
        const { el, editor } = await setupEditor(`<p>a</p>`, { config: { Plugins } });
        /** @type import("../src/core/history_plugin").HistoryPlugin") */
        const historyPlugin = editor.plugins.find((p) => p.constructor.name === "history");
        const p = el.querySelector("p");

        historyPlugin.applyMutations([
            {
                attributeName: "class",
                id: historyPlugin.nodeToIdMap.get(p),
                oldValue: null,
                type: "attributes",
                value: "x y",
            },
        ]);

        expect(getContent(el)).toBe(`<p class="y">a</p>`);
    });

    test("should skip the mutations if no changes in state", async () => {
        const { el, editor } = await setupEditor(`<p class="y">a</p>`, { config: { Plugins } });

        /** @type import("../src/core/history_plugin").HistoryPlugin") */
        const historyPlugin = editor.plugins.find((p) => p.constructor.name === "history");
        const p = el.querySelector("p");
        p.className = "";
        p.className = "y";
        historyPlugin.handleObserverRecords();
        historyPlugin.revertMutations(historyPlugin.currentStep.mutations);

        expect(getContent(el)).toBe(`<p class="y">a</p>`);
    });
});

describe("makeSavePoint", () => {
    test("makeSavePoint should correctly revert mutations (1)", async () => {
        const { el, editor } = await setupEditor(
            `<p>a[b<span style="color: tomato;">c</span>d]e</p>`
        );
        // The HISTORY_STAGE_SELECTION should have been triggered by the click on
        // the editable. As we set the selection programmatically, we dispatch the
        // selection here for the commands that relies on it.
        // If the selection of the editor would be programatically set upon start
        // (like an autofocus feature), it would be the role of the autofocus
        // feature to trigger the HISTORY_STAGE_SELECTION.
        editor.dispatch("HISTORY_STAGE_SELECTION");
        const restore = editor.shared.makeSavePoint();
        editor.dispatch("FORMAT_BOLD");
        restore();
        expect(getContent(el)).toBe(`<p>a[b<span style="color: tomato;">c</span>d]e</p>`);
    });
    test("makeSavePoint keeps old draft mutations, discards new ones, and does not add an unnecessary step", async () => {
        const { el, editor } = await setupEditor(`<p>[]c</p>`);
        expect(editor.shared.getHistorySteps().length).toBe(1);
        const p = el.querySelector("p");
        // draft to save
        p.append(document.createTextNode("d"));
        expect(getContent(el)).toBe(`<p>[]cd</p>`);
        const savepoint = editor.shared.makeSavePoint();
        // draft to discard
        p.append(document.createTextNode("e"));
        expect(getContent(el)).toBe(`<p>[]cde</p>`);
        savepoint();
        expect(getContent(el)).toBe(`<p>[]cd</p>`);
        expect(editor.shared.getHistorySteps().length).toBe(1);
    });
    test("applying a makeSavePoint consumes ulterior reversible steps and adds a new consumed step, while handling draft mutations", async () => {
        const { el, editor, plugins } = await setupEditor(`<p>[]c</p>`);
        const historyPlugin = plugins.get("history");
        expect(editor.shared.getHistorySteps().length).toBe(1);
        const p = el.querySelector("p");
        // draft to save
        p.append(document.createTextNode("d"));
        expect(getContent(el)).toBe(`<p>[]cd</p>`);
        const savepoint = editor.shared.makeSavePoint();
        // step to consume
        editor.shared.domInsert("z");
        editor.dispatch("ADD_STEP");
        let steps = editor.shared.getHistorySteps();
        expect(steps.length).toBe(2);
        const zStep = steps.at(-1);
        expect(historyPlugin.stepsStates.get(zStep.id)).toBe(undefined);
        // draft to discard
        p.append(document.createTextNode("e"));
        expect(getContent(el)).toBe(`<p>z[]cde</p>`);
        savepoint();
        expect(getContent(el)).toBe(`<p>[]cd</p>`);
        steps = editor.shared.getHistorySteps();
        expect(steps.length).toBe(3);
        expect(steps.at(-2)).toBe(zStep);
        expect(historyPlugin.stepsStates.get(zStep.id)).toBe("consumed");
        expect(historyPlugin.stepsStates.get(steps.at(-1).id)).toBe("consumed");
        undo(editor);
        expect(getContent(el)).toBe(`<p>[]c</p>`);
        redo(editor);
        // `d` was still a draft, redo can not reinsert `z` since it is consumed
        expect(getContent(el)).toBe(`<p>[]c</p>`);
    });
    test.todo("makeSavePoint should correctly revert mutations (2)", async () => {
        // TODO @phoenix: ensure that this spec also applies to complete steps (with undo/redo).
        // In the meantime, avoid adding observed DOM nodes to disconnected nodes as this is not fully
        // supported.
        // Before, the makeSavePoint method was reverting all the current mutations to finally re-apply
        // the old ones.
        // The current limitation of the editor is that newly created element that is not connected to
        // the DOM is not observed by the MutationObserver. The list of mutations resulted from an
        // operation can therefore be incomplete and cannot be re-applied. The goal of this test is to
        // verify that the makeSavePoint does not revert more mutation that it should.

        const { el, editor } = await setupEditor("<p>this is another paragraph with color 2</p>");

        const history = editor.plugins.find((plugin) => plugin.constructor.name === "history");
        const p = queryOne("p");
        const font = document.createElement("font");
        // The following line cause a REMOVE since the child does not belong to the p element anymore
        // The font element is not observed by the mutation observer, the ADD mutation is therefore not
        // recorded.
        font.appendChild(p.childNodes[0]);
        p.before(font);
        const numberOfSteps = history.steps.length;
        const safePoint = history.makeSavePoint();
        safePoint();
        expect(getContent(el)).toBe("<font>this is another paragraph with color 2</font><p></p>");
        expect(history.steps.length).toBe(numberOfSteps);
    });
});

describe("makePreviewableOperation", () => {
    test("makePreviewableOperation correctly revert previews", async () => {
        const { editor } = await setupEditor(`<div id="test"></div>`);

        const history = editor.plugins.find((plugin) => plugin.constructor.name === "history");
        const div = queryOne("#test");
        const previewableAddParagraph = history.makePreviewableOperation((elemId) => {
            const newElem = document.createElement("p");
            newElem.setAttribute("id", elemId);
            div.appendChild(newElem);
        });
        const numberOfSteps = history.steps.length;
        const numberOfCurrentMutations = history.currentStep.mutations.length;
        previewableAddParagraph.preview("first");
        await animationFrame();
        expect(history.steps.length).toBe(numberOfSteps);
        expect("#first").toHaveCount(1);
        previewableAddParagraph.preview("second");
        await animationFrame();
        expect(history.steps.length).toBe(numberOfSteps);
        expect("#first").toHaveCount(0);
        expect("#second").toHaveCount(1);
        previewableAddParagraph.revert();
        await animationFrame();
        expect("#first").toHaveCount(0);
        expect("#second").toHaveCount(0);
        expect(history.steps.length).toBe(numberOfSteps);
        expect(history.currentStep.mutations.length).toBe(numberOfCurrentMutations);
    });

    test("makePreviewableOperation correctly commit operation", async () => {
        const { editor } = await setupEditor(`<div id="test"></div>`);

        const history = editor.plugins.find((plugin) => plugin.constructor.name === "history");
        const div = queryOne("#test");
        const previewableAddParagraph = history.makePreviewableOperation((elemId) => {
            const newElem = document.createElement("p");
            newElem.setAttribute("id", elemId);
            div.appendChild(newElem);
        });
        const numberOfSteps = history.steps.length;
        previewableAddParagraph.preview("first");
        await animationFrame();
        expect(history.steps.length).toBe(numberOfSteps);
        expect("#first").toHaveCount(1);
        previewableAddParagraph.commit("second");
        await animationFrame();
        expect("#first").toHaveCount(0);
        expect("#second").toHaveCount(1);
        expect(history.steps.length).toBe(numberOfSteps + 1);
    });
});

describe("shortcut", () => {
    test("undo/redo with shortcut", async () => {
        const { editor, el } = await setupEditor(`<p>[]</p>`);

        await insertText(editor, "abc");
        await press(["ctrl", "z"]);
        await press(["cmd", "z"]);
        expect(getContent(el)).toBe("<p>ab[]</p>");

        await press(["ctrl", "y"]);
        expect(getContent(el)).toBe("<p>abc[]</p>");

        await press(["ctrl", "shift", "z"]);
        expect(getContent(el)).toBe("<p>abc[]</p>");
    });

    test("undo/redo with shortcut on macOS", async () => {
        mockUserAgent("mac");
        const { editor, el } = await setupEditor(`<p>[]</p>`);

        await insertText(editor, "abc");
        await press(["cmd", "z"]);
        await press(["cmd", "z"]);
        expect(getContent(el)).toBe("<p>a[]</p>");

        await press(["cmd", "y"]);
        expect(getContent(el)).toBe("<p>ab[]</p>");

        await press(["cmd", "shift", "z"]);
        expect(getContent(el)).toBe("<p>abc[]</p>");
    });

    test("canUndo canRedo", async () => {
        const state = {};
        const onChange = () => {
            state.canUndo = editor.shared.canUndo();
            state.canRedo = editor.shared.canRedo();
        };
        const { editor, el } = await setupEditor(`<p>[]</p>`, {
            config: { onChange },
        });
        expect(state).toEqual({});
        await insertText(editor, "a");
        expect(state).toEqual({ canUndo: true, canRedo: false });
        editor.dispatch("HISTORY_UNDO");
        expect(state).toEqual({ canUndo: false, canRedo: true });
        editor.dispatch("HISTORY_REDO");
        expect(state).toEqual({ canUndo: true, canRedo: false });
        editor.dispatch("HISTORY_UNDO");
        expect(state).toEqual({ canUndo: false, canRedo: true });
        await insertText(editor, "b");
        expect(state).toEqual({ canUndo: true, canRedo: false });
        expect(getContent(el)).toBe("<p>b[]</p>");
    });

    test("use handleNewRecords resource", async () => {
        patchWithCleanup(Editor.prototype, {
            dispatch(cmd, ...args) {
                if (cmd === "CONTENT_UPDATED") {
                    expect.step("CONTENT_UPDATED");
                }
                return super.dispatch(cmd, ...args);
            },
        });
        const onChange = () => {
            expect.step("onchange");
        };
        const resources = {
            handleNewRecords: () => {
                expect.step("handleNewRecords");
            },
        };
        const { editor } = await setupEditor(`<p>[]</p>`, {
            config: { onChange, resources },
        });
        expect.verifySteps([]);
        await insertText(editor, "a");
        expect.verifySteps([
            "handleNewRecords",
            "CONTENT_UPDATED",
            "handleNewRecords",
            "CONTENT_UPDATED",
            "onchange",
        ]);
    });
});

describe("destroy", () => {
    test("Mutations are not observed after history plugin is destroyed", async () => {
        // Observer is disconnected during cleanup.
        class TestPlugin extends Plugin {
            // Added history dependency so that this plugin is loaded after and unloaded before.
            static dependencies = ["history", "dom"];
            static name = "test";
            resources = {
                is_mutation_record_savable: this.isMutationRecordSavable.bind(this),
            };
            isMutationRecordSavable(record) {
                if (
                    record.type === "childList" &&
                    record.addedNodes.length === 1 &&
                    record.addedNodes.item(0).nodeType === Node.ELEMENT_NODE &&
                    record.addedNodes.item(0).matches(".test")
                ) {
                    expect.step("dispatch");
                    this.dispatch("DISPATCH");
                    return false;
                }
                return true;
            }
            destroy() {
                this.shared.domInsert(
                    parseHTML(this.document, `<div class="test">destroyed</div>`)
                );
            }
        }
        const Plugins = [...MAIN_PLUGINS, TestPlugin];
        const { editor } = await setupEditor(`<div>a[]b</div>`, { config: { Plugins } });
        // Ensure dispatch when plugins are alive.
        editor.shared.domInsert(parseHTML(editor.document, `<div class="test">destroyed</div>`));
        await animationFrame();
        expect.verifySteps(["dispatch"]);
        editor.destroy();
        await animationFrame();
        expect.verifySteps([]);
    });
});
