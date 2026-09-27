import { Plugin } from "@html_editor/plugin";
import { parseHTML } from "@html_editor/utils/html";
import { describe, expect, test } from "@odoo/hoot";
import { click, pointerDown, pointerUp, press, queryOne, microTick } from "@odoo/hoot-dom";
import { animationFrame, mockUserAgent, tick } from "@odoo/hoot-mock";
import { setupEditor, testEditor } from "./_helpers/editor";
import { getContent, setSelection } from "./_helpers/selection";
import { expectElementCount } from "./_helpers/ui_expectations";
import {
    commit,
    deleteBackward,
    ensureDistinctHistoryCommit,
    insertText,
    redo,
    splitBlock,
    undo,
} from "./_helpers/user_actions";
import { execCommand } from "./_helpers/userCommands";
import { nodeToTree } from "@html_editor/core/dom_reference_map_plugin";
import { HISTORY_COMMIT_TYPES } from "@html_editor/core/history_plugin";
import { NATIVE_MUTATION_TYPES } from "../src/core/dom_observer_plugin";

describe("reset", () => {
    test("should not add mutations in the current commit from the normalization when calling reset", async () => {
        const TestPlugin = class extends Plugin {
            static id = "test";
            resources = {
                normalize_processors: () => {
                    this.editable.firstChild.setAttribute("data-test-normalize", "1");
                    return this.editable;
                },
            };
        };
        const { el, plugins } = await setupEditor("<p>a</p>", {
            config: { includePlugins: [TestPlugin] },
        });
        const historyPlugin = plugins.get("history");
        expect(el.firstChild.getAttribute("data-test-normalize")).toBe("1");
        expect(historyPlugin.commits.length).toBe(1);
        const domObserverPlugin = plugins.get("domObserver");
        expect(domObserverPlugin.mutations.length).toBe(0);
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
        const domObserverPlugin = plugins.get("domObserver");
        expect(domObserverPlugin.mutations.length).toBe(0);

        await click(".odoo-editor-editable p");
        await animationFrame();
        await expectElementCount(".o-we-tablepicker", 0);
        expect(domObserverPlugin.mutations.length).toBe(0);
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
        editor.shared.history.commit();
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
                undo(editor); // <p>ab []cd</p> (grouped the two actions)
                undo(editor); // <p>ab []cd</p> (nothing to undo)
                redo(editor); // <p>a[]cd</p> (grouped the two actions)
                redo(editor); // <p>a[]cd</p> (nothing to redo)
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
                await ensureDistinctHistoryCommit();
                await insertText(editor, "b");
                await ensureDistinctHistoryCommit();
                await insertText(editor, "c");
                await ensureDistinctHistoryCommit();
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
                await ensureDistinctHistoryCommit();
                await insertText(editor, "b");
                await ensureDistinctHistoryCommit();
                await insertText(editor, "c");
                await ensureDistinctHistoryCommit();
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

    test("should type a, b, undo x2, redo, undo, redo x2", async () => {
        await testEditor({
            contentBefore: "<p>[]</p>",
            stepFunction: async (editor) => {
                await insertText(editor, "a");
                await insertText(editor, "b");
                undo(editor);
                undo(editor);
                redo(editor);
                undo(editor);
                redo(editor);
                redo(editor);
            },
            contentAfter: "<p>ab[]</p>",
        });
    });

    test("should discard draft mutations", async () => {
        const { el, editor } = await setupEditor(`<p>[]c</p>`);
        const p = el.querySelector("p");
        editor.shared.dom.insert("a");
        editor.shared.history.commit();
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
        await ensureDistinctHistoryCommit();
        expect(getContent(el)).toBe("<p>aA[]</p><p>b</p>", { message: "insert A" });
        editor.shared.selection.setCursorEnd(p2);
        await insertText(editor, "B");
        await ensureDistinctHistoryCommit();
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
        const domReferenceMapPlugin = plugins.get("domReferenceMap");
        const nodeId = domReferenceMapPlugin.getNodeId(pElement.firstChild);
        const selectionPlugin = plugins.get("selection");
        expect(selectionPlugin.currentData.selection).toEqual({
            anchorNodeId: nodeId,
            anchorOffset: 0,
            focusNodeId: nodeId,
            focusOffset: 0,
        });
        expect(getContent(el)).toBe("<p>[]a</p>");
    });
});

describe("commit", () => {
    test('should allow insertion of nested contenteditable="true"', async () => {
        await testEditor({
            contentBefore: `<div contenteditable="false"></div>`,
            stepFunction: async (editor) => {
                const editable = '<div contenteditable="true">abc</div>';
                editor.editable.querySelector("div").innerHTML = editable;
                editor.shared.history.commit();
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
    test("should prevent system classes to be added", async () => {
        await testEditor({
            contentBefore: `<p>a</p>`,
            stepFunction: async (editor) => {
                const p = editor.editable.querySelector("p");
                p.className = "x";
                editor.shared.history.commit();
                const history = editor.plugins.find((p) => p.constructor.id === "history");
                expect(history.commits.length).toBe(1);
            },
            config: { includePlugins: [TestSystemClassesPlugin] },
        });
    });

    test("system classes are ignored by history (neither added or removed)", async () => {
        const { editor, el } = await setupEditor(`<p>a[]</p>`, {
            config: { includePlugins: [TestSystemClassesPlugin] },
        });
        const p = editor.editable.querySelector("p");
        p.className = "x y";
        commit(editor);
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
                commit(editor);
                undo(editor);
                redo(editor);
            },
            contentAfter: `<p class="x">b[]</p>`,
            config: { includePlugins: [TestSystemClassesPlugin] },
        });
    });

    test("system attributes mutations are ignored by history", async () => {
        const { editor, el } = await setupEditor(`<p>a[]</p>`, {
            config: { includePlugins: [TestSystemClassesPlugin] },
        });
        const p = editor.editable.querySelector("p");
        p.setAttribute("data-x", "1");
        p.setAttribute("data-y", "1");
        commit(editor);
        undo(editor);
        expect(getContent(el)).toBe(`<p data-x="1">a[]</p>`);
        redo(editor);
        expect(getContent(el)).toBe(`<p data-x="1" data-y="1">a[]</p>`);
    });

    test("should skip the mutations if no changes in state", async () => {
        const { el, plugins } = await setupEditor(`<p class="y">a</p>`, {
            config: { includePlugins: [TestSystemClassesPlugin] },
        });

        /** @type {import("../src/core/dom_observer_plugin").DomObserverPlugin"} */
        const domObserverPlugin = plugins.get("domObserver");
        const p = el.querySelector("p");
        p.className = "";
        p.className = "y";
        domObserverPlugin.stagePendingMutations();
        domObserverPlugin.revertMutations(domObserverPlugin.mutations);

        expect(getContent(el)).toBe(`<p class="y">a</p>`);
    });

    test("should not copy system classes when changing a tag name", async () => {
        const { el, editor } = await setupEditor(`<p class="x">a[]</p>`, {
            config: { includePlugins: [TestSystemClassesPlugin] },
        });
        editor.shared.dom.setBlock({
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
        editor.shared.selection.stageSelection();
        const restore = editor.shared.history.makeSavePoint();
        execCommand(editor, "formatBold");
        restore();
        expect(getContent(el)).toBe(`<p>a[b<span style="color: tomato;">c</span>d]e</p>`);
    });
    test("makeSavePoint keeps old draft mutations, discards new ones, and does not add an unnecessary commit", async () => {
        const { el, editor } = await setupEditor(`<p>[]c</p>`);
        expect(editor.shared.history.getCommits().length).toBe(1);
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
        expect(editor.shared.history.getCommits().length).toBe(1);
    });
    test("applying a makeSavePoint reverses ulterior reversible commits and adds a new restore commit, while handling draft mutations", async () => {
        const { el, editor, plugins } = await setupEditor(`<p>[]c</p>`);
        const historyPlugin = plugins.get("history");
        expect(editor.shared.history.getCommits().length).toBe(1);
        const p = el.querySelector("p");
        // draft to save
        p.append(document.createTextNode("d"));
        expect(getContent(el)).toBe(`<p>[]cd</p>`);
        const savepoint = editor.shared.history.makeSavePoint();
        // commit to revert
        editor.shared.dom.insert("z");
        editor.shared.history.commit();
        let commits = editor.shared.history.getCommits();
        expect(commits.length).toBe(2);
        const zCommit = commits.at(-1);
        // draft to discard
        p.append(document.createTextNode("e"));
        expect(getContent(el)).toBe(`<p>z[]cde</p>`);
        savepoint();
        expect(getContent(el)).toBe(`<p>[]cd</p>`);
        commits = editor.shared.history.getCommits();
        expect(commits.length).toBe(3);
        expect(commits.at(-2)).toBe(zCommit);
        expect(historyPlugin.discardedCommits.has(zCommit.id)).toBe(true);
        expect(commits.at(-1).type).toBe(HISTORY_COMMIT_TYPES.RESTORE);
        undo(editor);
        expect(getContent(el)).toBe(`<p>[]c</p>`);
        redo(editor);
        // `d` was still a draft that got discarded on undo
        expect(getContent(el)).toBe(`<p>[]c</p>`);
    });
    test.todo("makeSavePoint should correctly revert mutations (2)", async () => {
        // TODO @phoenix: ensure that this spec also applies to complete commits (with undo/redo).
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
        const numberOfCommits = history.commits.length;
        const savePoint = history.makeSavePoint();
        savePoint();
        expect(getContent(el)).toBe("<font>this is another paragraph with color 2</font><p></p>");
        expect(history.commits.length).toBe(numberOfCommits);
    });
    test("makeSavePoint should correctly revert mutations and restore the history", async () => {
        const { el, editor } = await setupEditor(`<p>a[]</p>`);
        await insertText(editor, "b");
        expect(getContent(el)).toBe(`<p>ab[]</p>`);

        undo(editor);
        expect(getContent(el)).toBe(`<p>a[]</p>`);

        const restore = editor.shared.history.makeSavePoint();
        await insertText(editor, "c");
        expect(getContent(el)).toBe(`<p>ac[]</p>`);

        restore();
        expect(getContent(el)).toBe(`<p>a[]</p>`);

        redo(editor);
        expect(getContent(el)).toBe(`<p>ab[]</p>`);
    });
    test("makeSavePoint restores a selection invalidated by the reverted mutations", async () => {
        const { el, editor } = await setupEditor(`<p>abc</p>`);
        setSelection({
            anchorNode: el.firstChild,
            anchorOffset: 0,
            focusNode: el.firstChild,
            focusOffset: 1,
        });
        editor.shared.selection.stageSelection();
        const restore = editor.shared.history.makeSavePoint();
        editor.shared.format.requestFormat("underline", { applyStyle: true, commit: false });
        restore();
        expect(getContent(el)).toBe(`<p>[abc]</p>`);
    });
});

describe("makePreviewableOperation", () => {
    test("makePreviewableOperation correctly revert previews", async () => {
        const { plugins } = await setupEditor(`<div id="test"></div>`);

        const history = plugins.get("history");
        const domObserver = plugins.get("domObserver");
        const div = queryOne("#test");
        const previewableAddParagraph = history.makePreviewableOperation((elemId) => {
            const newElem = document.createElement("p");
            newElem.setAttribute("id", elemId);
            div.appendChild(newElem);
        });
        let numberOfCommits = history.commits.length;
        const numberOfCurrentMutations = domObserver.mutations.length;
        previewableAddParagraph.preview("first");
        // commit added by the preview
        numberOfCommits += 1;
        await animationFrame();
        expect(history.commits.length).toBe(numberOfCommits);
        expect("#first").toHaveCount(1);
        previewableAddParagraph.preview("second");
        // commit added by the revert of the first preview and the second preview
        numberOfCommits += 2;
        await animationFrame();
        expect(history.commits.length).toBe(numberOfCommits);
        expect("#first").toHaveCount(0);
        expect("#second").toHaveCount(1);
        previewableAddParagraph.revert();
        // commit added by the revert
        numberOfCommits += 1;
        await animationFrame();
        expect("#first").toHaveCount(0);
        expect("#second").toHaveCount(0);
        expect(history.commits.length).toBe(numberOfCommits);
        expect(domObserver.mutations.length).toBe(numberOfCurrentMutations);
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
        let numberOfCommits = history.commits.length;
        previewableAddParagraph.preview("first");
        // commit added by the preview
        numberOfCommits += 1;
        await animationFrame();
        expect(history.commits.length).toBe(numberOfCommits);
        expect("#first").toHaveCount(1);
        previewableAddParagraph.commit("second");
        // commit added by the revert due to the commit and the commit in itself
        numberOfCommits += 2;
        await animationFrame();
        expect("#first").toHaveCount(0);
        expect("#second").toHaveCount(1);
        expect(history.commits.length).toBe(numberOfCommits);
    });
});

describe("shortcut", () => {
    test("undo/redo with shortcut", async () => {
        const { editor, el } = await setupEditor(`<p>[]</p>`);

        await insertText(editor, "a");
        await ensureDistinctHistoryCommit();
        await insertText(editor, "b");
        await ensureDistinctHistoryCommit();
        await insertText(editor, "c");
        await ensureDistinctHistoryCommit();
        await press(["ctrl", "z"]);
        await press(["cmd", "z"]);
        expect(getContent(el)).toBe("<p>ab[]</p>");
        await press(["ctrl", "z"]);
        expect(getContent(el)).toBe("<p>a[]</p>");

        await press(["ctrl", "y"]);
        expect(getContent(el)).toBe("<p>ab[]</p>");
        await press(["ctrl", "y"]);
        expect(getContent(el)).toBe("<p>abc[]</p>");

        await press(["ctrl", "shift", "z"]);
        expect(getContent(el)).toBe("<p>abc[]</p>");
    });

    test("undo/redo with shortcut on macOS", async () => {
        mockUserAgent("mac");
        const { editor, el } = await setupEditor(`<p>[]</p>`);

        await insertText(editor, "a");
        await ensureDistinctHistoryCommit();
        await insertText(editor, "b");
        await ensureDistinctHistoryCommit();
        await insertText(editor, "c");

        expect(getContent(el)).toBe("<p>abc[]</p>");
        await press(["cmd", "z"]);
        expect(getContent(el)).toBe("<p>ab[]</p>");
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

    test("use on_pending_mutations_staged_handlers resource", async () => {
        const onChange = () => {
            expect.step("onchange");
        };
        const resources = {
            on_pending_mutations_staged_handlers: () => {
                expect.step("handleNewRecords");
            },
            on_content_updated_handlers: () => {
                expect.step("contentUpdated");
            },
            normalize_processors: (root) => {
                expect.step("normalize");
                root.classList.add("test");
                return root;
            },
        };
        const { editor } = await setupEditor(`<p>[]</p>`, {
            config: { onChange, resources },
        });
        expect.verifySteps(["normalize"]);
        await insertText(editor, "a");
        expect.verifySteps([
            // mutations for "a" insertion register new records for the current commit
            "handleNewRecords",
            "normalize",
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
                is_mutation_savable_predicates: this.isMutationSavable.bind(this),
            };
            /**
             * @param {import("../src/core/dom_observer_plugin").NativeMutation} mutation
             * @returns {boolean | undefined}
             */
            isMutationSavable(mutation) {
                if (
                    mutation.type === NATIVE_MUTATION_TYPES.CHILD_LIST &&
                    mutation.addedNodes.length === 1 &&
                    mutation.addedNodes[0].nodeType === Node.ELEMENT_NODE &&
                    mutation.addedNodes[0].matches(".test")
                ) {
                    expect.step("dispatch");
                    return false;
                }
            }
            destroy() {
                this.dependencies.dom.insert(
                    parseHTML(this.document, `<div class="test oe_unbreakable">destroyed</div>`)
                );
            }
        }
        const { editor } = await setupEditor(`<div class="oe_unbreakable">a[]b</div>`, {
            config: { includePlugins: [TestPlugin] },
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

        editor.shared.domObserver.applyCustomMutation({
            apply: () => {
                expect.step("custom apply");
            },
            revert: () => {
                expect.step("custom revert");
            },
        });
        editor.shared.history.commit();
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
        await ensureDistinctHistoryCommit();

        editor.shared.domObserver.applyCustomMutation({
            apply: () => {
                expect.step("custom apply");
            },
            revert: () => {
                expect.step("custom revert");
            },
        });
        await insertText(editor, "b");
        await ensureDistinctHistoryCommit();
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
        editor.shared.history.commit();
        expect(getContent(el)).toBe(`<p>[]testa</p>`);
        // Replace text node with a new one with the same content
        p.replaceChild(editor.document.createTextNode("a"), textNode);
        // `commit` returns false when there are no mutations
        expect(editor.shared.history.commit()).toBe(false);
    });
    test("same text node mutation should not break history", async () => {
        const { el, editor } = await setupEditor(`<p>[]hello </p>`);
        const p = el.querySelector("p");
        const textNode = editor.document.createTextNode("world");
        p.append(textNode);
        editor.shared.history.commit();
        expect(getContent(el)).toBe(`<p>[]hello world</p>`);
        // Replace text node with a new one with the same content
        p.replaceChild(editor.document.createTextNode("world"), textNode);
        // It should not create a commit but, the old node should be remapped to
        // the new one and history keep working
        expect(editor.shared.history.commit()).toBe(false);
        editor.shared.history.undo();
        expect(getContent(el)).toBe(`<p>[]hello </p>`);
        editor.shared.history.redo();
        expect(getContent(el)).toBe(`<p>[]hello world</p>`);
    });
    test("same text node mutation on newly added node should not break history", async () => {
        const { el, editor } = await setupEditor(`<p>[]hello </p>`);
        const p = el.querySelector("p");
        const textNode = editor.document.createTextNode("world");
        p.append(textNode);
        expect(getContent(el)).toBe(`<p>[]hello world</p>`);
        p.replaceChild(textNode.cloneNode(true), textNode);
        editor.shared.history.commit();
        expect(getContent(el)).toBe(`<p>[]hello world</p>`);
        editor.shared.history.undo();
        expect(getContent(el)).toBe(`<p>[]hello </p>`);
        editor.shared.history.redo();
        expect(getContent(el)).toBe(`<p>[]hello world</p>`);
    });
});

describe("unobserved mutations", () => {
    const withCommit = (editor, callback) => {
        callback();
        editor.shared.history.commit();
    };

    describe("classes", () => {
        test("unobserved class mutations should not be affected by undo/redo", async () => {
            const { editor } = await setupEditor(`<p>test</p>`);
            /** @type {HTMLElement} */
            const p = editor.editable.querySelector("p");
            withCommit(editor, () => p.classList.add("a"));
            editor.shared.domObserver.ignore(() => p.classList.add("b"));
            withCommit(editor, () => p.classList.add("c"));
            editor.shared.history.undo();
            expect(p.className).toBe("a b");
            editor.shared.domObserver.ignore(() => p.classList.remove("b"));
            editor.shared.history.redo();
            expect(p.className).toBe("a c");
        });
        test("no-op class removal should not be added to history", async () => {
            const { editor } = await setupEditor(`<p>test</p>`);
            /** @type {HTMLElement} */
            const p = editor.editable.querySelector("p");
            withCommit(editor, () => p.classList.add("a"));
            editor.shared.domObserver.ignore(() => p.classList.add("b"));
            withCommit(editor, () => p.classList.remove("b")); // no-op from a history perspective
            editor.shared.history.undo();
            expect(p.className).toBe("");
        });
        test("no-op class addition should not be added to history", async () => {
            const { editor } = await setupEditor(`<p class="a b">test</p>`);
            /** @type {HTMLElement} */
            const p = editor.editable.querySelector("p");
            withCommit(editor, () => p.classList.remove("a"));
            editor.shared.domObserver.ignore(() => p.classList.remove("b"));
            withCommit(editor, () => p.classList.add("b")); // no-op from a history perspective
            editor.shared.history.undo();
            expect(p.className).toBe("b a");
        });
        describe("fixClassListMutationsToEnsureNewMutations method", () => {
            test("should produce mutations in undo commit even with no class change", async () => {
                const { editor } = await setupEditor(`<p>test</p>`);
                /** @type {HTMLElement} */
                const p = editor.editable.querySelector("p");
                withCommit(editor, () => p.classList.add("a"));
                editor.shared.domObserver.ignore(() => p.classList.remove("a"));
                expect(p.className).toBe("");
                editor.shared.history.undo(); // mutation to be added to history: remove "a"
                expect(p.className).toBe("");
                editor.shared.history.redo();
                expect(p.className).toBe("a");
            });
            test("should add class 'x' to match oldValue's state", async () => {
                const { editor, plugins } = await setupEditor(`<p>test</p>`);
                const domObserverPlugin = plugins.get("domObserver");
                const p = editor.editable.querySelector("p");
                editor.shared.domReferenceMap.set(p, "testNodeId");
                const mutations = [
                    {
                        type: "classList",
                        nodeId: "testNodeId",
                        className: "x",
                        oldValue: true,
                        value: false,
                    },
                ];
                domObserverPlugin.fixClassListMutationsToEnsureNewMutations(mutations);
                expect(p).toHaveClass("x");
            });
            test("should not add class 'x' as state alread matches oldValue", async () => {
                const { editor, plugins } = await setupEditor(`<p>test</p>`);
                const domObserverPlugin = plugins.get("domObserver");
                const p = editor.editable.querySelector("p");
                editor.shared.domReferenceMap.set(p, "testNodeId");
                const mutations = [
                    {
                        type: "classList",
                        nodeId: "testNodeId",
                        className: "x",
                        oldValue: false,
                        value: true,
                    },
                ];
                domObserverPlugin.fixClassListMutationsToEnsureNewMutations(mutations);
                expect(p).not.toHaveClass("x");
            });
            test("should not add class 'x' as state alread matches first mutation's oldValue", async () => {
                const { editor, plugins } = await setupEditor(`<p>test</p>`);
                const domObserverPlugin = plugins.get("domObserver");
                const p = editor.editable.querySelector("p");
                editor.shared.domReferenceMap.set(p, "testNodeId");
                const mutations = [
                    {
                        type: "classList",
                        nodeId: "testNodeId",
                        className: "x",
                        oldValue: false,
                        value: true,
                    },
                    {
                        type: "classList",
                        nodeId: "testNodeId",
                        className: "x",
                        oldValue: true,
                        value: false,
                    },
                ];
                domObserverPlugin.fixClassListMutationsToEnsureNewMutations(mutations);
                expect(p).not.toHaveClass("x");
            });
        });
    });
    describe("attributes", () => {
        test("unobserved attribute mutations should not affect history", async () => {
            const { editor } = await setupEditor(`<p>test</p>`);
            /** @type {HTMLElement} */
            const p = editor.editable.querySelector("p");
            withCommit(editor, () => p.setAttribute("data-test", "a"));
            editor.shared.domObserver.ignore(() => p.setAttribute("data-test", "b"));
            withCommit(editor, () => p.setAttribute("data-test", "c"));
            editor.shared.history.undo();
            expect(p.getAttribute("data-test")).toBe("a");
        });
        test("multiple unobserved attribute mutations", async () => {
            const { editor } = await setupEditor(`<p>test</p>`);
            /** @type {HTMLElement} */
            const p = editor.editable.querySelector("p");
            withCommit(editor, () => p.setAttribute("data-test", "a"));
            editor.shared.domObserver.ignore(() => p.setAttribute("data-test", "b"));
            editor.shared.domObserver.ignore(() => p.setAttribute("data-test", "c"));
            withCommit(editor, () => p.setAttribute("data-test", "d"));
            editor.shared.history.undo();
            expect(p.getAttribute("data-test")).toBe("a");
        });
        test("setting an attribute as first observed commit", async () => {
            const { editor } = await setupEditor(`<p>test</p>`);
            /** @type {HTMLElement} */
            const p = editor.editable.querySelector("p");
            editor.shared.domObserver.ignore(() => p.setAttribute("data-test", "a"));
            withCommit(editor, () => p.setAttribute("data-test", "b"));
            editor.shared.history.undo();
            expect(p.getAttribute("data-test")).toBe(null);
        });
        test("attribute with no value", async () => {
            const { editor } = await setupEditor(`<p>test</p>`);
            /** @type {HTMLElement} */
            const p = editor.editable.querySelector("p");
            withCommit(editor, () => p.setAttribute("data-test", ""));
            editor.shared.domObserver.ignore(() => p.setAttribute("data-test", "a"));
            withCommit(editor, () => p.setAttribute("data-test", "b"));
            editor.shared.history.undo();
            expect(p.getAttribute("data-test")).toBe("");
        });
        test("no-op attribute change should not be added to history", async () => {
            const { editor } = await setupEditor(`<p data-test="a">test</p>`);
            /** @type {HTMLElement} */
            const p = editor.editable.querySelector("p");
            withCommit(editor, () => p.setAttribute("data-test", "b"));
            editor.shared.domObserver.ignore(() => p.setAttribute("data-test", "c"));
            withCommit(editor, () => p.setAttribute("data-test", "b")); // no-op from a history perspective
            editor.shared.history.undo();
            expect(p.getAttribute("data-test")).toBe("a");
        });
        test("should produce a undo commit even with no attribute change", async () => {
            const { editor } = await setupEditor(`<p data-test="a">test</p>`);
            /** @type {HTMLElement} */
            const p = editor.editable.querySelector("p");
            withCommit(editor, () => p.setAttribute("data-test", "b"));
            editor.shared.domObserver.ignore(() => p.setAttribute("data-test", "a"));
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
            withCommit(editor, () => (textNode.textContent = "a"));
            await ensureDistinctHistoryCommit();
            editor.shared.domObserver.ignore(() => (textNode.textContent = "b"));
            withCommit(editor, () => (textNode.textContent = "c"));
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
            withCommit(editor, () => parent.append(childA));
            editor.shared.domObserver.ignore(() => parent.append(childB));
            withCommit(editor, () => parent.replaceChildren());
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
            withCommit(editor, () => parent.append(nodeA));
            const nodeB = editor.document.createElement("span");
            // B is an unobserved node
            editor.shared.domObserver.ignore(() => nodeA.append(nodeB));
            const nodeC = editor.document.createElement("span");
            // addition of C to B should not be observed, thus empty commit
            withCommit(editor, () => nodeB.append(nodeC));
            editor.shared.history.undo();
            // addition of A is reverted
            expect(nodeA.parentNode).toBe(null);
        });
        test("node addition to descendant of unobserved node is not observed", async () => {
            const { editor } = await setupEditor(`<p></p>`);
            const p = editor.editable.querySelector("p");
            const nodeA = editor.document.createElement("span");
            const nodeB = editor.document.createElement("span");
            nodeA.append(nodeB);
            editor.shared.domObserver.ignore(() => p.append(nodeA));
            const nodeC = editor.document.createElement("span");
            withCommit(editor, () => nodeB.append(nodeC)); // should be an empty commit
            expect(editor.shared.history.getCommits().length).toBe(1);
        });
    });

    describe("snapshot commit", () => {
        test("unobserved nodes should be ignored in snapshot commit", async () => {
            const { editor, plugins } = await setupEditor(`<p>p1</p>`);
            const p1 = editor.editable.querySelector("p");
            // Insert unobserved node as direct child of editable
            const p2 = editor.document.createElement("p");
            p2.textContent = "p2";
            editor.shared.domObserver.ignore(() => editor.editable.append(p2));
            expect(getContent(editor.editable)).toBe("<p>p1</p><p>p2</p>");
            // Only p1 should be present in the snapshot commit
            const snapshotCommit = editor.shared.history.createSnapshotCommit();
            expect(snapshotCommit.data.mutations.length).toBe(1);
            const childNodeId = snapshotCommit.data.mutations[0].nodeId;
            const domReferenceMapPlugin = plugins.get("domReferenceMap");
            expect(domReferenceMapPlugin.getNodeById(childNodeId)).toBe(p1);
        });
        test("unobserved nodes should be ignored in snapshot commit (2)", async () => {
            const { editor } = await setupEditor(`<p>test</p>`);
            const p = editor.editable.querySelector("p");
            // Insert unobserved node as child of p (thus, not direct child of editable)
            const span = editor.document.createElement("span");
            span.textContent = "unobserved";
            editor.shared.domObserver.ignore(() => p.append(span));
            expect(getContent(editor.editable)).toBe("<p>test<span>unobserved</span></p>");
            // Only p and its text node should be present in the snapshot commit
            const snapshotCommit = editor.shared.history.createSnapshotCommit();
            expect(snapshotCommit.data.mutations.length).toBe(1);
            const serializedNode = snapshotCommit.data.mutations[0].serializedNode;
            expect(serializedNode.tagName).toBe("P");
            const pChildren = serializedNode.children;
            expect(pChildren.length).toBe(1);
            expect(pChildren[0].nodeType).toBe(Node.TEXT_NODE);
            expect(pChildren[0].textValue).toBe("test");
        });
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

        const domObserverPlugin = plugins.get("domObserver");
        const mutations = domObserverPlugin.mutations;
        const domReferenceMapPlugin = plugins.get("domReferenceMap");
        const idToNode = (id) => domReferenceMapPlugin.getNodeById(id);

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

        const domObserverPlugin = plugins.get("domObserver");
        const domReferenceMapPlugin = plugins.get("domReferenceMap");
        const mutations = domObserverPlugin.mutations;
        const idToNode = (id) => domReferenceMapPlugin.getNodeById(id);

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
        const domReferenceMapPlugin = plugins.get("domReferenceMap");
        const p = el.querySelector("p");
        const textNode = editor.document.createTextNode("test");
        p.prepend(textNode);
        editor.shared.history.commit();
        const serializedNode = domReferenceMapPlugin.serializeTree(nodeToTree(textNode));
        const unserializedTextNode = domReferenceMapPlugin.unserializeNode(serializedNode);
        expect(unserializedTextNode).toBe(textNode);
    });
});

describe("mutations order", () => {
    test("should revert mutations in the correct order", async () => {
        const { el, editor } = await setupEditor(`<p>[]<br></p>`);
        const p = el.querySelector("p");
        p.replaceChildren(editor.document.createTextNode("a"), editor.document.createTextNode("b"));
        editor.shared.history.commit();
        await ensureDistinctHistoryCommit();
        expect(getContent(el)).toBe(`<p>[]ab</p>`);
        p.replaceChildren();
        editor.shared.history.commit();
        editor.shared.history.undo();
        expect(getContent(el)).toBe(`<p>[]ab</p>`);
    });
});

describe("grouped undo/redo", () => {
    test("should undo, then redo all changes on common text node", async () => {
        const { editor, el } = await setupEditor("<p>[]</p>");
        await insertText(editor, "abc");
        const abc = getContent(el);
        await splitBlock(editor);
        const abc_ = getContent(el);
        await insertText(editor, "def");
        const abc_def = getContent(el);
        await splitBlock(editor);
        const abc_def_ = getContent(el);
        await insertText(editor, "ghi");
        const abc_def_ghi = getContent(el);
        await splitBlock(editor);
        const abc_def_ghi_ = getContent(el);
        await expectElementCount("p", 4);
        expect(abc_def_ghi_).toBe(
            `<p>abc</p><p>def</p><p>ghi</p><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`
        );
        await undo(editor);
        expect(getContent(el)).toBe(abc_def_ghi);
        await undo(editor);
        expect(getContent(el)).toBe(abc_def_);
        await undo(editor);
        expect(getContent(el)).toBe(abc_def);
        await undo(editor);
        expect(getContent(el)).toBe(abc_);
        await undo(editor);
        expect(getContent(el)).toBe(abc);
        await redo(editor);
        expect(getContent(el)).toBe(abc_);
        await redo(editor);
        expect(getContent(el)).toBe(abc_def);
        await redo(editor);
        expect(getContent(el)).toBe(abc_def_);
        await redo(editor);
        expect(getContent(el)).toBe(abc_def_ghi);
        await redo(editor);
        expect(getContent(el)).toBe(abc_def_ghi_);
    });
});
