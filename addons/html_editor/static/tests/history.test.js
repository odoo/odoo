import { Plugin } from "@html_editor/plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { parseHTML } from "@html_editor/utils/html";
import { describe, expect, test } from "@odoo/hoot";
import { click, pointerDown, pointerUp, press, queryOne, microTick } from "@odoo/hoot-dom";
import { animationFrame, mockUserAgent, tick } from "@odoo/hoot-mock";
import { setupEditor, testEditor } from "./_helpers/editor";
import { getContent, setSelection } from "./_helpers/selection";
import { expectElementCount } from "./_helpers/ui_expectations";
import { addStep, deleteBackward, insertText, redo, undo } from "./_helpers/user_actions";
import { execCommand } from "./_helpers/userCommands";

describe("reset", () => {
    test("should not add mutations in the current step from the normalization when calling reset", async () => {
        const TestPlugin = class extends Plugin {
            static id = "test";
            resources = {
                normalize_handlers: () => {
                    this.editable.firstChild.setAttribute("data-test-normalize", "1");
                },
            };
        };
        const { el, plugins } = await setupEditor("<p>a</p>", {
            config: { Plugins: [...MAIN_PLUGINS, TestPlugin] },
        });
        const historyPlugin = plugins.get("history");
        expect(el.firstChild.getAttribute("data-test-normalize")).toBe("1");
        expect(historyPlugin.steps.length).toBe(1);
        expect(historyPlugin.currentStep.mutations.length).toBe(0);
    });

    test.tags("desktop");
    test("open table picker shouldn't add mutations", async () => {
        const { editor, el, plugins } = await setupEditor("<p>[]</p>");

        await insertText(editor, "/tab");
        await press("enter");
        await animationFrame();
        await expectElementCount(".o-we-tablepicker", 1);
        expect(getContent(el)).toBe(
            `<p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]</p>`
        );
        const historyPlugin = plugins.get("history");
        expect(historyPlugin.currentStep.mutations.length).toBe(0);

        await click(".odoo-editor-editable p");
        await animationFrame();
        await expectElementCount(".o-we-tablepicker", 0);
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
        editor.shared.dom.insert("a");
        editor.shared.history.addStep();
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
        editor.shared.dom.insert("a");
        editor.shared.history.addStep();
        undo(editor);
        expect(getContent(el)).toBe(`<p>[]c</p>`);
        p.prepend(document.createTextNode("b"));
        redo(editor);
        expect(getContent(el)).toBe(`<p>a[]c</p>`);
        undo(editor);
        expect(getContent(el)).toBe(`<p>[]c</p>`);
    });

    test("undo then redo, then re-undo, then re-redo and set the selection where we expect it", async () => {
        const { editor, el } = await setupEditor("<p>a</p><p>b</p>");
        const [p1, p2] = editor.editable.querySelectorAll("p");
        editor.shared.selection.setCursorEnd(p1);
        // DO
        await insertText(editor, "A");
        expect(getContent(el)).toBe("<p>aA[]</p><p>b</p>", { message: "insert A" });
        editor.shared.selection.setCursorEnd(p2);
        await insertText(editor, "B");
        expect(getContent(el)).toBe("<p>aA</p><p>bB[]</p>", { message: "insert B" });
        // UNDO
        await press(["ctrl", "z"]);
        expect(getContent(el)).toBe("<p>aA</p><p>b[]</p>", { message: "undo insert B" });
        await press(["ctrl", "z"]);
        expect(getContent(el)).toBe("<p>a[]</p><p>b</p>", { message: "undo insert A" });
        // REDO
        await press(["ctrl", "y"]);
        expect(getContent(el)).toBe("<p>aA[]</p><p>b</p>", { message: "redo insert A" });
        await press(["ctrl", "y"]);
        expect(getContent(el)).toBe("<p>aA</p><p>bB[]</p>", { message: "redo insert B" });
        // REUNDO
        await press(["ctrl", "z"]);
        expect(getContent(el)).toBe("<p>aA</p><p>b[]</p>", { message: "undo insert B" });
        await press(["ctrl", "z"]);
        expect(getContent(el)).toBe("<p>a[]</p><p>b</p>", { message: "undo insert A" });
        // REREDO
        await press(["ctrl", "y"]);
        expect(getContent(el)).toBe("<p>aA[]</p><p>b</p>", { message: "redo insert A" });
        await press(["ctrl", "y"]);
        expect(getContent(el)).toBe("<p>aA</p><p>bB[]</p>", { message: "redo insert B" });
    });
});

describe("selection", () => {
    test("should stage the selection upon click", async () => {
        const { el, plugins } = await setupEditor("<p>a</p>");
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
        const historyPlugin = plugins.get("history");
        const nodeId = historyPlugin.nodeMap.getId(pElement.firstChild);
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
                editor.shared.history.addStep();
            },
            contentAfter: `<div contenteditable="false"><div contenteditable="true">abc</div></div>`,
        });
    });
});

describe("system classes and attributes", () => {
    class TestSystemClassesPlugin extends Plugin {
        static id = "testRenderClasses";
        resources = {
            system_classes: ["x"],
            system_attributes: ["data-x"],
        };
    }
    const Plugins = [...MAIN_PLUGINS, TestSystemClassesPlugin];
    test("should prevent system classes to be added", async () => {
        await testEditor({
            contentBefore: `<p>a</p>`,
            stepFunction: async (editor) => {
                const p = editor.editable.querySelector("p");
                p.className = "x";
                editor.shared.history.addStep();
                const history = editor.plugins.find((p) => p.constructor.id === "history");
                expect(history.steps.length).toBe(1);
            },
            config: { Plugins: Plugins },
        });
    });

    test("system classes are ignored by history (neither added or removed)", async () => {
        const { editor, el } = await setupEditor(`<p>a[]</p>`, { config: { Plugins: Plugins } });
        const p = editor.editable.querySelector("p");
        p.className = "x y";
        addStep(editor);
        undo(editor);
        expect(getContent(el)).toBe(`<p class="x">a[]</p>`);
        redo(editor);
        expect(getContent(el)).toBe(`<p class="x y">a[]</p>`);
    });

    test("system class with char mutation", async () => {
        await testEditor({
            contentBefore: `<p>a[]</p>`,
            stepFunction: async (editor) => {
                const p = editor.editable.querySelector("p");
                p.className = "x";
                p.textContent = "b";
                editor.shared.selection.setCursorEnd(p);
                addStep(editor);
                undo(editor);
                redo(editor);
            },
            contentAfter: `<p class="x">b[]</p>`,
            config: { Plugins: Plugins },
        });
    });

    test("system attributes mutations are ignored by history", async () => {
        const { editor, el } = await setupEditor(`<p>a[]</p>`, { config: { Plugins: Plugins } });
        const p = editor.editable.querySelector("p");
        p.setAttribute("data-x", "1");
        p.setAttribute("data-y", "1");
        addStep(editor);
        undo(editor);
        expect(getContent(el)).toBe(`<p data-x="1">a[]</p>`);
        redo(editor);
        expect(getContent(el)).toBe(`<p data-x="1" data-y="1">a[]</p>`);
    });

    test("should skip the mutations if no changes in state", async () => {
        const { el, plugins } = await setupEditor(`<p class="y">a</p>`, { config: { Plugins } });

        /** @type import("../src/core/history_plugin").HistoryPlugin") */
        const historyPlugin = plugins.get("history");
        const p = el.querySelector("p");
        p.className = "";
        p.className = "y";
        historyPlugin.handleObserverRecords();
        historyPlugin.revertMutations(historyPlugin.currentStep.mutations);

        expect(getContent(el)).toBe(`<p class="y">a</p>`);
    });

    test("should not copy system classes when changing a tag name", async () => {
        const { el, editor } = await setupEditor(`<p class="x">a[]</p>`, { config: { Plugins } });
        editor.shared.dom.setTag({
            tagName: "h1",
        });
        expect(getContent(el)).toBe(`<h1>a[]</h1>`);
    });
});

describe("makeSavePoint", () => {
    test("makeSavePoint should correctly revert mutations (1)", async () => {
        const { el, editor } = await setupEditor(
            `<p>a[b<span style="color: tomato;">c</span>d]e</p>`
        );
        // The stageSelection should have been triggered by the click on
        // the editable. As we set the selection programmatically, we dispatch the
        // selection here for the commands that relies on it.
        // If the selection of the editor would be programatically set upon start
        // (like an autofocus feature), it would be the role of the autofocus
        // feature to trigger the stageSelection.
        editor.shared.history.stageSelection();
        const restore = editor.shared.history.makeSavePoint();
        execCommand(editor, "formatBold");
        restore();
        expect(getContent(el)).toBe(`<p>a[b<span style="color: tomato;">c</span>d]e</p>`);
    });
    test("makeSavePoint keeps old draft mutations, discards new ones, and does not add an unnecessary step", async () => {
        const { el, editor } = await setupEditor(`<p>[]c</p>`);
        expect(editor.shared.history.getHistorySteps().length).toBe(1);
        const p = el.querySelector("p");
        // draft to save
        p.append(document.createTextNode("d"));
        expect(getContent(el)).toBe(`<p>[]cd</p>`);
        const savepoint = editor.shared.history.makeSavePoint();
        // draft to discard
        p.append(document.createTextNode("e"));
        expect(getContent(el)).toBe(`<p>[]cde</p>`);
        savepoint();
        expect(getContent(el)).toBe(`<p>[]cd</p>`);
        expect(editor.shared.history.getHistorySteps().length).toBe(1);
    });
    test("applying a makeSavePoint consumes ulterior reversible steps and adds a new consumed step, while handling draft mutations", async () => {
        const { el, editor, plugins } = await setupEditor(`<p>[]c</p>`);
        const historyPlugin = plugins.get("history");
        expect(editor.shared.history.getHistorySteps().length).toBe(1);
        const p = el.querySelector("p");
        // draft to save
        p.append(document.createTextNode("d"));
        expect(getContent(el)).toBe(`<p>[]cd</p>`);
        const savepoint = editor.shared.history.makeSavePoint();
        // step to consume
        editor.shared.dom.insert("z");
        editor.shared.history.addStep();
        let steps = editor.shared.history.getHistorySteps();
        expect(steps.length).toBe(2);
        const zStep = steps.at(-1);
        expect(historyPlugin.stepsStates.get(zStep.id)).toBe(undefined);
        // draft to discard
        p.append(document.createTextNode("e"));
        expect(getContent(el)).toBe(`<p>z[]cde</p>`);
        savepoint();
        expect(getContent(el)).toBe(`<p>[]cd</p>`);
        steps = editor.shared.history.getHistorySteps();
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

        const { el, plugins } = await setupEditor("<p>this is another paragraph with color 2</p>");

        const history = plugins.get("history");
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
        const { plugins } = await setupEditor(`<div id="test"></div>`);

        const history = plugins.get("history");
        const div = queryOne("#test");
        const previewableAddParagraph = history.makePreviewableOperation((elemId) => {
            const newElem = document.createElement("p");
            newElem.setAttribute("id", elemId);
            div.appendChild(newElem);
        });
        let numberOfSteps = history.steps.length;
        const numberOfCurrentMutations = history.currentStep.mutations.length;
        previewableAddParagraph.preview("first");
        // step added by the preview
        numberOfSteps += 1;
        await animationFrame();
        expect(history.steps.length).toBe(numberOfSteps);
        expect("#first").toHaveCount(1);
        previewableAddParagraph.preview("second");
        // step added by the revert of the first preview and the second preview
        numberOfSteps += 2;
        await animationFrame();
        expect(history.steps.length).toBe(numberOfSteps);
        expect("#first").toHaveCount(0);
        expect("#second").toHaveCount(1);
        previewableAddParagraph.revert();
        // step added by the revert
        numberOfSteps += 1;
        await animationFrame();
        expect("#first").toHaveCount(0);
        expect("#second").toHaveCount(0);
        expect(history.steps.length).toBe(numberOfSteps);
        expect(history.currentStep.mutations.length).toBe(numberOfCurrentMutations);
    });

    test("makePreviewableOperation correctly commit operation", async () => {
        const { plugins } = await setupEditor(`<div id="test"></div>`);

        const history = plugins.get("history");
        const div = queryOne("#test");
        const previewableAddParagraph = history.makePreviewableOperation((elemId) => {
            const newElem = document.createElement("p");
            newElem.setAttribute("id", elemId);
            div.appendChild(newElem);
        });
        let numberOfSteps = history.steps.length;
        previewableAddParagraph.preview("first");
        // step added by the preview
        numberOfSteps += 1;
        await animationFrame();
        expect(history.steps.length).toBe(numberOfSteps);
        expect("#first").toHaveCount(1);
        previewableAddParagraph.commit("second");
        // step added by the revert due to the commit and the commit in itself
        numberOfSteps += 2;
        await animationFrame();
        expect("#first").toHaveCount(0);
        expect("#second").toHaveCount(1);
        expect(history.steps.length).toBe(numberOfSteps);
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
            state.canUndo = editor.shared.history.canUndo();
            state.canRedo = editor.shared.history.canRedo();
        };
        const { editor, el } = await setupEditor(`<p>[]</p>`, {
            config: { onChange },
        });
        expect(state).toEqual({});
        await insertText(editor, "a");
        expect(state).toEqual({ canUndo: true, canRedo: false });
        execCommand(editor, "historyUndo");
        expect(state).toEqual({ canUndo: false, canRedo: true });
        execCommand(editor, "historyRedo");
        expect(state).toEqual({ canUndo: true, canRedo: false });
        execCommand(editor, "historyUndo");
        expect(state).toEqual({ canUndo: false, canRedo: true });
        await insertText(editor, "b");
        expect(state).toEqual({ canUndo: true, canRedo: false });
        expect(getContent(el)).toBe("<p>b[]</p>");
    });

    test("use handleNewRecords resource", async () => {
        const onChange = () => {
            expect.step("onchange");
        };
        const resources = {
            handleNewRecords: () => {
                expect.step("handleNewRecords");
            },
            content_updated_handlers: () => {
                expect.step("contentUpdated");
            },
        };
        const { editor } = await setupEditor(`<p>[]</p>`, {
            config: { onChange, resources },
        });
        expect.verifySteps([]);
        await insertText(editor, "a");
        expect.verifySteps([
            // mutations for "a" insertion register new records for the current step
            "handleNewRecords",
            "contentUpdated",
            // mutations for the hint removal are filtered out (no registered record)
            "contentUpdated",
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
            static id = "test";
            resources = {
                savable_mutation_record_predicates: this.isMutationRecordSavable.bind(this),
            };
            isMutationRecordSavable(record) {
                if (
                    record.type === "childList" &&
                    record.addedTrees.length === 1 &&
                    record.addedTrees[0].node.nodeType === Node.ELEMENT_NODE &&
                    record.addedTrees[0].node.matches(".test")
                ) {
                    expect.step("dispatch");
                    return false;
                }
                return true;
            }
            destroy() {
                this.dependencies.dom.insert(
                    parseHTML(this.document, `<div class="test oe_unbreakable">destroyed</div>`)
                );
            }
        }
        const Plugins = [...MAIN_PLUGINS, TestPlugin];
        const { editor } = await setupEditor(`<div class="oe_unbreakable">a[]b</div>`, {
            config: { Plugins },
        });
        // Ensure dispatch when plugins are alive.
        editor.shared.dom.insert(
            parseHTML(editor.document, `<div class="test oe_unbreakable">destroyed</div>`)
        );
        await animationFrame();
        expect.verifySteps(["dispatch"]);
        editor.destroy();
        await animationFrame();
        expect.verifySteps([]);
    });
});

describe("custom mutation", () => {
    test("should apply/revert custom mutation", async () => {
        const { el, editor } = await setupEditor(`<p>[]c</p>`);
        const restoreSavePoint = editor.shared.history.makeSavePoint();
        await insertText(editor, "a");

        editor.shared.history.applyCustomMutation({
            apply: () => {
                expect.step("custom apply");
            },
            revert: () => {
                expect.step("custom revert");
            },
        });
        editor.shared.history.addStep();
        expect.verifySteps(["custom apply"]);
        expect(getContent(el)).toBe(`<p>a[]c</p>`);

        undo(editor);
        expect.verifySteps(["custom revert"]);
        expect(getContent(el)).toBe(`<p>a[]c</p>`);

        undo(editor);
        expect.verifySteps([]);
        expect(getContent(el)).toBe(`<p>[]c</p>`);

        redo(editor);
        expect.verifySteps([]);
        expect(getContent(el)).toBe(`<p>a[]c</p>`);

        redo(editor);
        expect.verifySteps(["custom apply"]);
        expect(getContent(el)).toBe(`<p>a[]c</p>`);

        undo(editor);
        expect.verifySteps(["custom revert"]);
        expect(getContent(el)).toBe(`<p>a[]c</p>`);

        restoreSavePoint();
        expect.verifySteps(["custom apply", "custom revert", "custom apply", "custom revert"]);
    });

    test("should apply/revert custom mutation with dom mutation", async () => {
        const { el, editor } = await setupEditor(`<p>[]c</p>`);
        const restoreSavePoint = editor.shared.history.makeSavePoint();
        await insertText(editor, "a");

        editor.shared.history.applyCustomMutation({
            apply: () => {
                expect.step("custom apply");
            },
            revert: () => {
                expect.step("custom revert");
            },
        });
        await insertText(editor, "b");
        expect.verifySteps(["custom apply"]);
        expect(getContent(el)).toBe(`<p>ab[]c</p>`);

        undo(editor);
        expect.verifySteps(["custom revert"]);
        expect(getContent(el)).toBe(`<p>a[]c</p>`);

        undo(editor);
        expect.verifySteps([]);
        expect(getContent(el)).toBe(`<p>[]c</p>`);

        redo(editor);
        expect.verifySteps([]);
        expect(getContent(el)).toBe(`<p>a[]c</p>`);

        redo(editor);
        expect.verifySteps(["custom apply"]);
        expect(getContent(el)).toBe(`<p>ab[]c</p>`);

        undo(editor);
        expect.verifySteps(["custom revert"]);
        expect(getContent(el)).toBe(`<p>a[]c</p>`);

        restoreSavePoint();
        expect.verifySteps(["custom apply", "custom revert", "custom apply", "custom revert"]);
    });
});

describe("same text node mutations", () => {
    test("should not record same text mutation", async () => {
        const { el, editor } = await setupEditor(`<p>[]test</p>`);
        const p = el.querySelector("p");
        const textNode = editor.document.createTextNode("a");
        p.append(textNode);
        editor.shared.history.addStep();
        expect(getContent(el)).toBe(`<p>[]testa</p>`);
        // Replace text node with a new one with the same content
        p.replaceChild(editor.document.createTextNode("a"), textNode);
        // addStep returns false when there are no mutations
        expect(editor.shared.history.addStep()).toBe(false);
    });
    test("same text node mutation should not break history", async () => {
        const { el, editor } = await setupEditor(`<p>[]hello </p>`);
        const p = el.querySelector("p");
        const textNode = editor.document.createTextNode("world");
        p.append(textNode);
        editor.shared.history.addStep();
        expect(getContent(el)).toBe(`<p>[]hello world</p>`);
        // Replace text node with a new one with the same content
        p.replaceChild(editor.document.createTextNode("world"), textNode);
        // It should not create a step but, the old node should be remapped to
        // the new one and history keep working
        expect(editor.shared.history.addStep()).toBe(false);
        editor.shared.history.undo();
        expect(getContent(el)).toBe(`<p>[]hello </p>`);
        editor.shared.history.redo();
        expect(getContent(el)).toBe(`<p>[]hello world</p>`);
    });
    test("same text node mutation with another mutation should not break history", async () => {
        const { el, editor } = await setupEditor(`<p>[]hello </p>`);
        const p = el.querySelector("p");
        p.append(editor.document.createTextNode("dear "));
        const textNode = editor.document.createTextNode("world");
        p.append(textNode);
        expect(getContent(el)).toBe(`<p>[]hello dear world</p>`);
        // Replace text node with a new one with the same content
        p.replaceChild(textNode.cloneNode(true), textNode);
        editor.shared.history.addStep();
        expect(getContent(el)).toBe(`<p>[]hello dear world</p>`);
        editor.shared.history.undo();
        expect(getContent(el)).toBe(`<p>[]hello </p>`);
        editor.shared.history.redo();
        expect(getContent(el)).toBe(`<p>[]hello dear world</p>`);
    });
});

describe("unobserved mutations", () => {
    const withAddStep = (editor, callback) => {
        callback();
        editor.shared.history.addStep();
    };

    describe("classes", () => {
        test("unobserved class mutations should not be affected by undo/redo", async () => {
            const { editor } = await setupEditor(`<p>test</p>`);
            /** @type {HTMLElement} */
            const p = editor.editable.querySelector("p");
            withAddStep(editor, () => p.classList.add("a"));
            editor.shared.history.ignoreDOMMutations(() => p.classList.add("b"));
            withAddStep(editor, () => p.classList.add("c"));
            editor.shared.history.undo();
            expect(p.className).toBe("a b");
            editor.shared.history.ignoreDOMMutations(() => p.classList.remove("b"));
            editor.shared.history.redo();
            expect(p.className).toBe("a c");
        });
        test("no-op class removal should not be added to history", async () => {
            const { editor } = await setupEditor(`<p>test</p>`);
            /** @type {HTMLElement} */
            const p = editor.editable.querySelector("p");
            withAddStep(editor, () => p.classList.add("a"));
            editor.shared.history.ignoreDOMMutations(() => p.classList.add("b"));
            withAddStep(editor, () => p.classList.remove("b")); // no-op from a history perspective
            editor.shared.history.undo();
            expect(p.className).toBe("");
        });
        test("no-op class addition should not be added to history", async () => {
            const { editor } = await setupEditor(`<p class="a b">test</p>`);
            /** @type {HTMLElement} */
            const p = editor.editable.querySelector("p");
            withAddStep(editor, () => p.classList.remove("a"));
            editor.shared.history.ignoreDOMMutations(() => p.classList.remove("b"));
            withAddStep(editor, () => p.classList.add("b")); // no-op from a history perspective
            editor.shared.history.undo();
            expect(p.className).toBe("b a");
        });
        test("should produce mutations in undo step even with no class change", async () => {
            const { editor } = await setupEditor(`<p>test</p>`);
            /** @type {HTMLElement} */
            const p = editor.editable.querySelector("p");
            withAddStep(editor, () => p.classList.add("a"));
            editor.shared.history.ignoreDOMMutations(() => p.classList.remove("a"));
            expect(p.className).toBe("");
            editor.shared.history.undo(); // mutation to be added to history: remove "a"
            expect(p.className).toBe("");
            editor.shared.history.redo();
            expect(p.className).toBe("a");
        });
    });
    describe("attributes", () => {
        test("unobserved attribute mutations should not affect history", async () => {
            const { editor } = await setupEditor(`<p>test</p>`);
            /** @type {HTMLElement} */
            const p = editor.editable.querySelector("p");
            withAddStep(editor, () => p.setAttribute("data-test", "a"));
            editor.shared.history.ignoreDOMMutations(() => p.setAttribute("data-test", "b"));
            withAddStep(editor, () => p.setAttribute("data-test", "c"));
            editor.shared.history.undo();
            expect(p.getAttribute("data-test")).toBe("a");
        });
        test("multiple unobserved attribute mutations", async () => {
            const { editor } = await setupEditor(`<p>test</p>`);
            /** @type {HTMLElement} */
            const p = editor.editable.querySelector("p");
            withAddStep(editor, () => p.setAttribute("data-test", "a"));
            editor.shared.history.ignoreDOMMutations(() => p.setAttribute("data-test", "b"));
            editor.shared.history.ignoreDOMMutations(() => p.setAttribute("data-test", "c"));
            withAddStep(editor, () => p.setAttribute("data-test", "d"));
            editor.shared.history.undo();
            expect(p.getAttribute("data-test")).toBe("a");
        });
        test("setting an attribute as first observed step", async () => {
            const { editor } = await setupEditor(`<p>test</p>`);
            /** @type {HTMLElement} */
            const p = editor.editable.querySelector("p");
            editor.shared.history.ignoreDOMMutations(() => p.setAttribute("data-test", "a"));
            withAddStep(editor, () => p.setAttribute("data-test", "b"));
            editor.shared.history.undo();
            expect(p.getAttribute("data-test")).toBe(null);
        });
        test("attribute with no value", async () => {
            const { editor } = await setupEditor(`<p>test</p>`);
            /** @type {HTMLElement} */
            const p = editor.editable.querySelector("p");
            withAddStep(editor, () => p.setAttribute("data-test", ""));
            editor.shared.history.ignoreDOMMutations(() => p.setAttribute("data-test", "a"));
            withAddStep(editor, () => p.setAttribute("data-test", "b"));
            editor.shared.history.undo();
            expect(p.getAttribute("data-test")).toBe("");
        });
        test("no-op attribute change should not be added to history", async () => {
            const { editor } = await setupEditor(`<p data-test="a">test</p>`);
            /** @type {HTMLElement} */
            const p = editor.editable.querySelector("p");
            withAddStep(editor, () => p.setAttribute("data-test", "b"));
            editor.shared.history.ignoreDOMMutations(() => p.setAttribute("data-test", "c"));
            withAddStep(editor, () => p.setAttribute("data-test", "b")); // no-op from a history perspective
            editor.shared.history.undo();
            expect(p.getAttribute("data-test")).toBe("a");
        });
        test("should produce a undo step even with no attribute change", async () => {
            const { editor } = await setupEditor(`<p data-test="a">test</p>`);
            /** @type {HTMLElement} */
            const p = editor.editable.querySelector("p");
            withAddStep(editor, () => p.setAttribute("data-test", "b"));
            editor.shared.history.ignoreDOMMutations(() => p.setAttribute("data-test", "a"));
            editor.shared.history.undo(); // mutation to be added to history: set "data-test" to "a"
            expect(p.getAttribute("data-test")).toBe("a");
            editor.shared.history.redo();
            expect(p.getAttribute("data-test")).toBe("b");
        });
    });
    describe("character data", () => {
        test("unobserved character data mutations should not affect history", async () => {
            const { editor } = await setupEditor(`<p>test</p>`);
            /** @type {HTMLElement} */
            const textNode = editor.editable.querySelector("p").firstChild;
            withAddStep(editor, () => (textNode.textContent = "a"));
            editor.shared.history.ignoreDOMMutations(() => (textNode.textContent = "b"));
            withAddStep(editor, () => (textNode.textContent = "c"));
            editor.shared.history.undo();
            expect(textNode.textContent).toBe("a");
        });
    });

    describe("childList", () => {
        test("unobserved childList mutations should not affect history", async () => {
            const { editor } = await setupEditor(`<p><span></span></p>`);
            /** @type {HTMLElement} */
            const parent = editor.editable.querySelector("p span");
            const childA = editor.document.createElement("span");
            const childB = editor.document.createElement("span");
            withAddStep(editor, () => parent.append(childA));
            editor.shared.history.ignoreDOMMutations(() => parent.append(childB));
            withAddStep(editor, () => parent.replaceChildren());
            editor.shared.history.undo();
            const childNodes = [...parent.childNodes];
            expect(childNodes.length).toBe(1);
            expect(childNodes[0]).toBe(childA);
        });
        test("node addition to unobserved node is also unobserved", async () => {
            const { editor } = await setupEditor(`<p><span></span></p>`);
            /** @type {HTMLElement} */
            const parent = editor.editable.querySelector("p span");
            const nodeA = editor.document.createElement("span");
            withAddStep(editor, () => parent.append(nodeA));
            const nodeB = editor.document.createElement("span");
            // B is an unobserved node
            editor.shared.history.ignoreDOMMutations(() => nodeA.append(nodeB));
            const nodeC = editor.document.createElement("span");
            // addition of C to B should not be observed, thus empty step
            withAddStep(editor, () => nodeB.append(nodeC));
            editor.shared.history.undo();
            // addition of A is reverted
            expect(nodeA.parentNode).toBe(null);
        });
    });
    test("node addition to descendant of unobserved node is not observed", async () => {
        const { editor } = await setupEditor(`<p></p>`);
        const p = editor.editable.querySelector("p");
        const nodeA = editor.document.createElement("span");
        const nodeB = editor.document.createElement("span");
        nodeA.append(nodeB);
        editor.shared.history.ignoreDOMMutations(() => p.append(nodeA));
        const nodeC = editor.document.createElement("span");
        withAddStep(editor, () => nodeB.append(nodeC)); // should be an empty step
        expect(editor.shared.history.getHistorySteps().length).toBe(1);
    });
});

describe("serialization", () => {
    test("node serialization should not duplicate nodes", async () => {
        const { editor, el, plugins } = await setupEditor("<p>hello</p>");
        const p = el.querySelector("p");
        const textNode = p.firstChild;
        // Mutation: add strong to p
        const strong = editor.document.createElement("strong");
        p.append(strong);
        // Mutation: remove textNode
        textNode.remove();
        // Mutation: add textNode to strong
        strong.append(textNode);

        await microTick();

        const historyPlugin = plugins.get("history");
        const mutations = historyPlugin.currentStep.mutations;
        const idToNode = (id) => historyPlugin.nodeMap.getNode(id);

        expect(mutations.length).toBe(3);

        // Serialized node should not have textNode as child, even though it
        // current has it as child (otherwise it would duplicate it on unserialization)
        let { nodeId, children } = mutations[0].serializedNode;
        expect(idToNode(nodeId)).toBe(strong);
        expect(children.length).toBe(0);

        // 2nd and 3rd mutations: textNode is moved into strong
        ({ nodeId } = mutations[1].serializedNode);
        expect(idToNode(nodeId)).toBe(textNode);
        ({ nodeId } = mutations[2].serializedNode);
        expect(idToNode(nodeId)).toBe(textNode);
    });

    test("serialized node should have the childlist as it was at mutation time", async () => {
        const { editor, plugins } = await setupEditor(`<p><br></p>`);
        const p = editor.editable.querySelector("p");
        const [a, b, c, d] = ["a", "b", "c", "d"].map((name) => {
            const span = editor.document.createElement("span");
            span.className = name;
            return span;
        });
        // A is added with no children.
        p.append(a);

        // B is added having C as child.
        b.append(c); // B is not yet observed
        a.append(b); // B - C is added to A

        // D is added to A with no children.
        a.append(d);

        // C is moved from B to D (creates 2 records: removal and addition).
        d.append(c);

        await microTick();

        const historyPlugin = plugins.get("history");
        const mutations = historyPlugin.currentStep.mutations;
        const idToNode = (id) => historyPlugin.nodeMap.getNode(id);

        expect(mutations.length).toBe(5);

        // Serialized node A should not have children, even though it currently
        // has B and D as children.
        let { nodeId, children } = mutations[0].serializedNode;
        expect(idToNode(nodeId)).toBe(a);
        expect(children.length).toBe(0);

        // Serialized node B should have C as child, even though it currently
        // has no children
        ({ nodeId, children } = mutations[1].serializedNode);
        expect(idToNode(nodeId)).toBe(b);
        expect(children.length).toBe(1);
        expect(idToNode(children[0].nodeId)).toBe(c);

        // Serialized node D should not have children, even though it currently
        // has C as child.
        ({ nodeId, children } = mutations[2].serializedNode);
        expect(idToNode(nodeId)).toBe(d);
        expect(children.length).toBe(0);

        // Serialized node C should have no children
        ({ nodeId, children } = mutations[3].serializedNode);
        expect(idToNode(nodeId)).toBe(c);
        expect(children.length).toBe(0);

        ({ nodeId, children } = mutations[4].serializedNode);
        expect(idToNode(nodeId)).toBe(c);
        expect(children.length).toBe(0);
    });

    test("unserialization of text node should not duplicate an existing one", async () => {
        const { el, editor, plugins } = await setupEditor(`<p><br></p>`);
        const historyPlugin = plugins.get("history");
        const p = el.querySelector("p");
        const textNode = editor.document.createTextNode("test");
        p.prepend(textNode);
        editor.shared.history.addStep();
        const serializedNode = historyPlugin.serializeNode(textNode);
        const unserializedTextNode = historyPlugin.unserializeNode(serializedNode);
        expect(unserializedTextNode).toBe(textNode);
    });
});

describe("mutations order", () => {
    test("should revert mutations in the correct order", async () => {
        const { el, editor } = await setupEditor(`<p>[]<br></p>`);
        const p = el.querySelector("p");
        p.replaceChildren(editor.document.createTextNode("a"), editor.document.createTextNode("b"));
        editor.shared.history.addStep();
        expect(getContent(el)).toBe(`<p>[]ab</p>`);
        p.replaceChildren();
        editor.shared.history.addStep();
        editor.shared.history.undo();
        expect(getContent(el)).toBe(`<p>[]ab</p>`);
    });
});
