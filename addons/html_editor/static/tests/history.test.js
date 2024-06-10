import { expect, describe, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "./_helpers/editor";
import { addStep, deleteBackward, insertText, redo, undo } from "./_helpers/user_actions";
import { Plugin } from "@html_editor/plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { getContent, setSelection } from "./_helpers/selection";
import { pointerDown, pointerUp, press, queryOne } from "@odoo/hoot-dom";
import { animationFrame, mockUserAgent, tick } from "@odoo/hoot-mock";

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
                insertText(editor, "a");
                insertText(editor, "b");
                insertText(editor, "c");
                undo(editor);
                undo(editor);
                insertText(editor, "d");
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
                insertText(editor, "a");
                insertText(editor, "b");
                insertText(editor, "c");
                undo(editor);
                undo(editor);
                insertText(editor, "d");
                undo(editor);
                redo(editor);
                redo(editor);
            },
            contentAfter: "<p>ad[]</p>",
        });
    });
});

describe("selection", () => {
    test("should stage the selection upon click", async () => {
        const { el, editor } = await setupEditor("<p>a</p>");
        const pElement = queryOne("p");
        pointerDown(pElement);
        setSelection({
            anchorNode: pElement.firstChild,
            anchorOffset: 0,
            focusNode: pElement.firstChild,
            focusOffset: 0,
        });
        await tick();
        pointerUp(pElement);
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

describe("prevent renderingClasses to be set from history", () => {
    class TestRenderingClassesPlugin extends Plugin {
        static name = "testRenderClasses";
        static resources = () => ({
            history_rendering_classes: ["x"],
        });
    }
    const Plugins = [...MAIN_PLUGINS, TestRenderingClassesPlugin];
    test("should prevent renderingClasses to be added", async () => {
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

    test("should prevent renderingClasses to be added when adding 2 classes", async () => {
        await testEditor({
            contentBefore: `<p>a</p>`,
            stepFunction: async (editor) => {
                const p = editor.editable.querySelector("p");
                p.className = "x y";
                addStep(editor);
                undo(editor);
                redo(editor);
            },
            contentAfter: `[]<p class="y">a</p>`,
            config: { Plugins: Plugins },
        });
    });

    test("should prevent renderingClasses to be added in historyApply", async () => {
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
    test("makeSavePoint should correctly revert mutations (2)", async () => {
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

        insertText(editor, "abc");
        press(["ctrl", "z"]);
        press(["cmd", "z"]);
        expect(getContent(el)).toBe("<p>ab[]</p>");

        press(["ctrl", "y"]);
        expect(getContent(el)).toBe("<p>abc[]</p>");

        press(["ctrl", "shift", "z"]);
        expect(getContent(el)).toBe("<p>abc[]</p>");
    });

    test("undo/redo with shortcut on macOS", async () => {
        mockUserAgent("mac");
        const { editor, el } = await setupEditor(`<p>[]</p>`);

        insertText(editor, "abc");
        press(["cmd", "z"]);
        press(["cmd", "z"]);
        expect(getContent(el)).toBe("<p>a[]</p>");

        press(["cmd", "y"]);
        expect(getContent(el)).toBe("<p>ab[]</p>");

        press(["cmd", "shift", "z"]);
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
        insertText(editor, "a");
        expect(state).toEqual({ canUndo: true, canRedo: false });
        editor.dispatch("HISTORY_UNDO");
        expect(state).toEqual({ canUndo: false, canRedo: true });
        editor.dispatch("HISTORY_REDO");
        expect(state).toEqual({ canUndo: true, canRedo: false });
        editor.dispatch("HISTORY_UNDO");
        expect(state).toEqual({ canUndo: false, canRedo: true });
        insertText(editor, "b");
        expect(state).toEqual({ canUndo: true, canRedo: false });
        expect(getContent(el)).toBe("<p>b[]</p>");
    });
});
