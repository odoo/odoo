import {
    collaborativeObject,
    Counter,
    EmbeddedWrapper,
    EmbeddedWrapperMixin,
    embedding,
    offsetCounter,
    savedCounter,
    SavedCounter,
} from "@html_editor/../tests/_helpers/embedded_component";
import { EmbeddedComponentPlugin } from "@html_editor/others/embedded_component_plugin";
import {
    getEditableDescendants,
    StateChangeManager,
} from "@html_editor/others/embedded_component_utils";
import { parseHTML } from "@html_editor/utils/html";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { click, manuallyDispatchProgrammaticEvent } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { onMounted, onWillDestroy, xml } from "@odoo/owl";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    applyConcurrentActions,
    mergePeersSteps,
    renderTextualSelection,
    setupMultiEditor,
    testMultiEditor,
    validateContent,
    validateSameHistory,
} from "./_helpers/collaboration";
import { cleanHints } from "./_helpers/dispatch";
import { unformat } from "./_helpers/format";
import { getContent } from "./_helpers/selection";
import { addStep, deleteBackward, deleteForward, redo, undo } from "./_helpers/user_actions";
import { execCommand } from "./_helpers/userCommands";
import { wrapInlinesInBlocks } from "@html_editor/utils/dom";

/**
 * @param {Editor} editor
 * @param {string} value
 */
function insert(editor, value) {
    editor.shared.dom.insert(value);
    editor.shared.history.addStep();
}

describe("Conflict resolution", () => {
    test("all peer steps should be on the same order", async () => {
        const peerInfos = await setupMultiEditor({
            peerIds: ["c1", "c2", "c3"],
            contentBefore: "<p><x>a[c1}{c1]</x><y>e[c2}{c2]</y><z>i[c3}{c3]</z></p>",
        });
        applyConcurrentActions(peerInfos, {
            c1: (editor) => {
                insert(editor, "b");
                insert(editor, "c");
                insert(editor, "d");
            },
            c2: (editor) => {
                insert(editor, "f");
                insert(editor, "g");
                insert(editor, "h");
            },
            c3: (editor) => {
                insert(editor, "j");
                insert(editor, "k");
                insert(editor, "l");
            },
        });
        mergePeersSteps(peerInfos);
        validateSameHistory(peerInfos);

        renderTextualSelection(peerInfos);
        validateContent(
            peerInfos,
            "<p><x>abcd[c1}{c1]</x><y>efgh[c2}{c2]</y><z>ijkl[c3}{c3]</z></p>"
        );
    });

    test("should 2 peer insertText in 2 different paragraph", async () => {
        const peerInfos = await setupMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: "<p>ab[c1}{c1]</p><p>cd[c2}{c2]</p>",
        });
        applyConcurrentActions(peerInfos, {
            c1: (editor) => {
                insert(editor, "e");
            },
            c2: (editor) => {
                insert(editor, "f");
            },
        });
        mergePeersSteps(peerInfos);
        validateSameHistory(peerInfos);
        renderTextualSelection(peerInfos);
        validateContent(peerInfos, "<p>abe[c1}{c1]</p><p>cdf[c2}{c2]</p>");
    });

    test("should 2 peer insertText twice in 2 different paragraph", async () => {
        await testMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: "<p>ab[c1}{c1]</p><p>cd[c2}{c2]</p>",
            afterCreate: (peerInfos) => {
                applyConcurrentActions(peerInfos, {
                    c1: (editor) => {
                        insert(editor, "e");
                        insert(editor, "f");
                    },
                    c2: (editor) => {
                        insert(editor, "g");
                        insert(editor, "h");
                    },
                });
                mergePeersSteps(peerInfos);
                validateSameHistory(peerInfos);
            },
            contentAfter: "<p>abef[c1}{c1]</p><p>cdgh[c2}{c2]</p>",
        });
    });
    test("should insertText with peer 1 and deleteBackward with peer 2", async () => {
        await testMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: "<p>ab[c1}{c1][c2}{c2]c</p>",
            afterCreate: (peerInfos) => {
                applyConcurrentActions(peerInfos, {
                    c1: (editor) => {
                        insert(editor, "d");
                    },
                    c2: (editor) => {
                        deleteBackward(editor);
                    },
                });
                mergePeersSteps(peerInfos);
                validateSameHistory(peerInfos);
            },
            contentAfter: "<p>a[c2}{c2]d[c1}{c1]cc</p>",
        });
    });
    test("should insertText twice with peer 1 and deleteBackward twice with peer 2", async () => {
        await testMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: "<p>ab[c1}{c1][c2}{c2]c</p>",
            afterCreate: (peerInfos) => {
                applyConcurrentActions(peerInfos, {
                    c1: (editor) => {
                        insert(editor, "d");
                        insert(editor, "e");
                    },
                    c2: (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                });
                mergePeersSteps(peerInfos);
                validateSameHistory(peerInfos);
            },
            contentAfter: "<p>de[c1}{c1]c[c2}{c2]c</p>",
        });
    });
});
test("should not revert the step of another peer", async () => {
    await testMultiEditor({
        peerIds: ["c1", "c2"],
        contentBefore: "<p><x>a[c1}{c1]</x><y>b[c2}{c2]</y></p>",
        afterCreate: (peerInfos) => {
            applyConcurrentActions(peerInfos, {
                c1: (editor) => {
                    insert(editor, "c");
                },
                c2: (editor) => {
                    insert(editor, "d");
                },
            });
            mergePeersSteps(peerInfos);
            undo(peerInfos.c1.editor);
            undo(peerInfos.c2.editor);
            expect(peerInfos.c1.editor.editable).toHaveInnerHTML("<p><x>a</x><y>bd</y></p>", {
                message: "error with peer c1",
            });
            expect(peerInfos.c2.editor.editable).toHaveInnerHTML("<p><x>ac</x><y>b</y></p>", {
                message: "error with peer c2",
            });
        },
    });
});
describe("collaborative makeSavePoint", () => {
    test("After a savePoint, local steps should be discarded in collaboration and external steps should not", async () => {
        const peerInfos = await setupMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: `<p>[c1}{c1]<br></p><p>[c2}{c2]<br></p>`,
        });
        const savepoint = peerInfos.c1.editor.shared.history.makeSavePoint();
        insert(peerInfos.c2.editor, "a");
        mergePeersSteps(peerInfos);
        insert(peerInfos.c1.editor, "z");
        mergePeersSteps(peerInfos);
        insert(peerInfos.c2.editor, "b");
        mergePeersSteps(peerInfos);
        savepoint();
        mergePeersSteps(peerInfos);
        cleanHints(peerInfos.c1.editor);
        cleanHints(peerInfos.c2.editor);
        renderTextualSelection(peerInfos);
        expect(peerInfos.c1.editor.editable).toHaveInnerHTML(
            `<p>[c1}{c1]<br></p><p>ab[c2}{c2]</p>`
        );
        expect(peerInfos.c2.editor.editable).toHaveInnerHTML(
            `<p>[c1}{c1]<br></p><p>ab[c2}{c2]</p>`
        );
    });
    test("Ensure splitElement steps reversibility in the context of makeSavePoint", async () => {
        const peerInfos = await setupMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: `<p>a[c1}{c1]</p><p>b[c2}{c2]</p>`,
        });
        const e1 = peerInfos.c1.editor;
        const e2 = peerInfos.c2.editor;
        const savepoint = e2.shared.history.makeSavePoint();
        await manuallyDispatchProgrammaticEvent(e1.editable, "beforeinput", {
            inputType: "insertParagraph",
        });
        mergePeersSteps(peerInfos);
        insert(e1, "z");
        mergePeersSteps(peerInfos);
        savepoint();
        mergePeersSteps(peerInfos);
        expect(getContent(e1.editable)).toBe("<p>a</p><p>z[]</p><p>b</p>");
        expect(getContent(e2.editable)).toBe("<p>a</p><p>z</p><p>b[]</p>");
    });
});
describe("history addExternalStep", () => {
    test("should revert and re-apply local mutations that are not part of a finished step", async () => {
        const peerInfos = await setupMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: `<p>i[c1}{c1][c2}{c2]</p>`,
        });
        peerInfos.c1.editor.shared.dom.insert("b");
        insert(peerInfos.c2.editor, "a");
        mergePeersSteps(peerInfos);
        peerInfos.c1.editor.shared.history.addStep();
        mergePeersSteps(peerInfos);
        cleanHints(peerInfos.c1.editor);
        cleanHints(peerInfos.c2.editor);
        // TODO @phoenix c1 editable should be `<p>iab[]</p>`, but its selection
        // was not adjusted properly when receiving the external step
        expect(getContent(peerInfos.c1.editor.editable)).toBe(`<p>ia[]b</p>`);
        expect(getContent(peerInfos.c2.editor.editable)).toBe(`<p>ia[]b</p>`);
    });
});
test("wrapInlinesInBlocks should not create impossible mutations in a collaborative step", async () => {
    const peerInfos = await setupMultiEditor({
        peerIds: ["c1", "c2"],
        contentBefore: `<div class="oe_unbreakable">myNode[c1}{c1][c2}{c2]</div>`,
    });
    const e1 = peerInfos.c1.editor;
    const e2 = peerInfos.c2.editor;
    const div1 = e1.editable.querySelector("div");
    const cursors1 = e1.shared.selection.preserveSelection();
    wrapInlinesInBlocks(div1, cursors1);
    cursors1.restore();
    e1.shared.history.addStep();
    mergePeersSteps(peerInfos);
    expect(getContent(e1.editable, { sortAttrs: true })).toBe(
        '<p data-selection-placeholder=""><br></p>' +
            '<div class="oe_unbreakable"><p>myNode[]</p></div>' +
            '<p data-selection-placeholder=""><br></p>'
    );
    expect(getContent(e2.editable, { sortAttrs: true })).toBe(
        '<p data-selection-placeholder=""><br></p>' +
            '<div class="oe_unbreakable"><p>myNode[]</p></div>' +
            '<p data-selection-placeholder=""><br></p>'
    );
});
test("should reset from snapshot", async () => {
    await testMultiEditor({
        peerIds: ["c1", "c2"],
        contentBefore: "<p>a[c1}{c1]</p>",
        afterCreate: (peerInfos) => {
            insert(peerInfos.c1.editor, "b");
            peerInfos.c1.collaborationPlugin.makeSnapshot();
            // Insure the snapshot is considered to be older than 30 seconds.
            peerInfos.c1.collaborationPlugin.snapshots[0].time = 1;
            const { steps } = peerInfos.c1.collaborationPlugin.getSnapshotSteps();
            peerInfos.c2.collaborationPlugin.resetFromSteps(steps);

            expect(peerInfos.c2.historyPlugin.steps.map((x) => x.id)).toEqual([
                "fake_concurrent_id_1",
            ]);
            expect(peerInfos.c2.historyPlugin.steps[0].mutations.map((x) => x.nodeId)).toEqual([
                "fake_id_4",
            ]);
        },
        contentAfter: "<p>ab[c1}{c1]</p>",
    });
});
describe("steps whith no parent in history", () => {
    test("should be able to retreive steps when disconnected from peers that has send step", async () => {
        await testMultiEditor({
            peerIds: ["c1", "c2", "c3"],
            contentBefore: "<p><x>a[c1}{c1]</x><y>b[c2}{c2]</y><z>c[c3}{c3]</z></p>",
            afterCreate: (peerInfos) => {
                insert(peerInfos.c1.editor, "d");
                peerInfos.c2.collaborationPlugin.onExternalHistorySteps([
                    peerInfos.c1.historyPlugin.steps[1],
                ]);
                insert(peerInfos.c2.editor, "e");
                peerInfos.c1.collaborationPlugin.onExternalHistorySteps([
                    peerInfos.c2.historyPlugin.steps[2],
                ]);
                peerInfos.c3.collaborationPlugin.onExternalHistorySteps([
                    peerInfos.c2.historyPlugin.steps[2],
                ]);
                // receive step 1 after step 2
                peerInfos.c3.collaborationPlugin.onExternalHistorySteps([
                    peerInfos.c1.historyPlugin.steps[1],
                ]);
                validateSameHistory(peerInfos);
            },
            contentAfter: "<p><x>ad[c1}{c1]</x><y>be[c2}{c2]</y><z>c[c3}{c3]</z></p>",
        });
    });
    test("should receive steps where parent was not received", async () => {
        await testMultiEditor({
            peerIds: ["c1", "c2", "c3"],
            contentBefore: "<p><i>a[c1}{c1]</i><b>b[c2}{c2]</b></p>",
            afterCreate: (peerInfos) => {
                insert(peerInfos.c1.editor, "c");
                peerInfos.c2.collaborationPlugin.onExternalHistorySteps([
                    peerInfos.c1.historyPlugin.steps[1],
                ]);

                // Peer 3 connect firt to peer 1 that made a snapshot.

                peerInfos.c1.collaborationPlugin.makeSnapshot();
                // Fake the time of the snapshot so it is considered to be
                // older than 30 seconds.
                peerInfos.c1.collaborationPlugin.snapshots[0].time = 1;
                const { steps } = peerInfos.c1.collaborationPlugin.getSnapshotSteps();
                peerInfos.c3.collaborationPlugin.resetFromSteps(steps);

                // In the meantime peer 2 send the step to peer 1
                insert(peerInfos.c2.editor, "d");
                insert(peerInfos.c2.editor, "e");
                peerInfos.c1.collaborationPlugin.onExternalHistorySteps([
                    peerInfos.c2.historyPlugin.steps[2],
                ]);
                peerInfos.c1.collaborationPlugin.onExternalHistorySteps([
                    peerInfos.c2.historyPlugin.steps[3],
                ]);

                // Now peer 2 is connected to peer 3 and peer 2 make a new step.
                insert(peerInfos.c2.editor, "f");
                peerInfos.c1.collaborationPlugin.onExternalHistorySteps([
                    peerInfos.c2.historyPlugin.steps[4],
                ]);
                peerInfos.c3.collaborationPlugin.onExternalHistorySteps([
                    peerInfos.c2.historyPlugin.steps[4],
                ]);
            },
            contentAfter: "<p><i>ac[c1}{c1]</i><b>bdef[c2}{c2]</b></p>",
        });
    });
});
describe("sanitize", () => {
    beforeEach(() => patchWithCleanup(console, { log: expect.step }));

    const LOG_XSS = /* js */ `window.top.console.log("xss")`;

    test("should sanitize when adding a node", async () => {
        patchWithCleanup(console, {
            log: expect.step,
        });
        await testMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: "<p><x>a</x></p>",
            afterCreate: (peerInfos) => {
                const script = document.createElement("script");
                script.innerHTML = LOG_XSS;
                peerInfos.c1.editor.editable.append(script);
                addStep(peerInfos.c1.editor);
                expect(peerInfos.c1.historyPlugin.steps[1]).not.toBe(undefined);
                peerInfos.c2.collaborationPlugin.onExternalHistorySteps([
                    peerInfos.c1.historyPlugin.steps[1],
                ]);
                expect(peerInfos.c2.editor.editable).toHaveInnerHTML("<p><x>a</x></p>");
            },
        });
        expect.verifySteps(["xss"]);
    });
    test("should sanitize when adding a script as descendant", async () => {
        await testMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: "<p>a[c1}{c1][c2}{c2]</p>",
            afterCreate: (peerInfos) => {
                const document = peerInfos.c1.editor.document;
                const i = document.createElement("i");
                i.innerHTML = '<b>b</b><script>alert("c");</script>';
                peerInfos.c1.editor.editable.append(i);
                addStep(peerInfos.c1.editor);
                peerInfos.c2.collaborationPlugin.onExternalHistorySteps([
                    peerInfos.c1.historyPlugin.steps[1],
                ]);
            },
            afterCursorInserted: (peerInfos) => {
                expect(peerInfos.c2.editor.editable).toHaveInnerHTML(
                    "<p>a[c1}{c1][c2}{c2]</p><i><b>b</b></i>"
                );
            },
        });
    });
    test("should sanitize when changing an attribute", async () => {
        await testMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: "<p>a<img></p>",
            afterCreate: (peerInfos) => {
                const img = peerInfos.c1.editor.editable.childNodes[0].childNodes[1];
                img.setAttribute("class", "b");
                img.setAttribute("onerror", LOG_XSS);
                addStep(peerInfos.c1.editor);
                peerInfos.c2.collaborationPlugin.onExternalHistorySteps([
                    peerInfos.c1.historyPlugin.steps[1],
                ]);
                expect(peerInfos.c1.editor.editable).toHaveInnerHTML(
                    `<p>a<img class="b" onerror="${LOG_XSS.replace(/"/g, "&quot;")}"></p>`
                );
                expect(peerInfos.c2.editor.editable).toHaveInnerHTML('<p>a<img class="b"></p>');
            },
        });
    });

    test("should sanitize when undo is adding a script node", async () => {
        // Prevent console.warn from making the test fail due to inexistent node
        // to remove. The script node is non existent in the collaborator's DOM
        // (c2) because of sanitization of serialized nodes.
        patchWithCleanup(console, { warn: () => {} });
        await testMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: "<p>a</p>",
            afterCreate: (peerInfos) => {
                const script = document.createElement("script");
                script.innerHTML = LOG_XSS;
                peerInfos.c1.editor.editable.append(script);
                addStep(peerInfos.c1.editor);
                script.remove();
                addStep(peerInfos.c1.editor);
                peerInfos.c2.collaborationPlugin.onExternalHistorySteps([
                    peerInfos.c1.historyPlugin.steps[1],
                ]);
                // Change the peer in order to be undone from peer 2
                peerInfos.c1.historyPlugin.steps[2].peerId = "c2";
                peerInfos.c2.collaborationPlugin.onExternalHistorySteps([
                    peerInfos.c1.historyPlugin.steps[2],
                ]);
                execCommand(peerInfos.c2.editor, "historyUndo");
                expect(peerInfos.c2.editor.editable).toHaveInnerHTML("<p>a</p>");
            },
        });
        expect.verifySteps(["xss"]);
    });
    test("should sanitize when undo is adding a descendant script node", async () => {
        await testMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: "<p>a</p>",
            afterCreate: (peerInfos) => {
                const div = document.createElement("div");
                div.innerHTML = `<i>b</i><script>${LOG_XSS}</script>`;
                peerInfos.c1.editor.editable.append(div);
                addStep(peerInfos.c1.editor);
                div.remove();
                addStep(peerInfos.c1.editor);
                peerInfos.c2.collaborationPlugin.onExternalHistorySteps([
                    peerInfos.c1.historyPlugin.steps[1],
                ]);
                // Change the peer in order to be undone from peer 2
                peerInfos.c1.historyPlugin.steps[2].peerId = "c2";
                peerInfos.c2.collaborationPlugin.onExternalHistorySteps([
                    peerInfos.c1.historyPlugin.steps[2],
                ]);
                execCommand(peerInfos.c2.editor, "historyUndo");
                expect(peerInfos.c2.editor.editable).toHaveInnerHTML(
                    `<p>a</p><div class="o-paragraph"><i>b</i></div>`
                );
            },
        });
    });
    test("should sanitize when undo is changing an attribute", async () => {
        await testMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: "<p>a<img></p>",
            afterCreate: (peerInfos) => {
                const img = peerInfos.c1.editor.editable.childNodes[0].childNodes[1];
                img.setAttribute("class", "b");
                img.setAttribute("onerror", LOG_XSS);
                addStep(peerInfos.c1.editor);
                img.setAttribute("class", "");
                img.setAttribute("onerror", "");
                addStep(peerInfos.c1.editor);
                peerInfos.c2.collaborationPlugin.onExternalHistorySteps([
                    peerInfos.c1.historyPlugin.steps[1],
                ]);
                // Change the peer in order to be undone from peer 2
                peerInfos.c1.historyPlugin.steps[2].peerId = "c2";
                peerInfos.c2.collaborationPlugin.onExternalHistorySteps([
                    peerInfos.c1.historyPlugin.steps[2],
                ]);
                execCommand(peerInfos.c2.editor, "historyUndo");
                expect(peerInfos.c2.editor.editable).toHaveInnerHTML('<p>a<img class="b"></p>');
            },
        });
    });
    test("should not sanitize contenteditable attribute (check DOMPurify DEFAULT_ALLOWED_ATTR)", async () => {
        await testMultiEditor({
            peerIds: ["c1"],
            contentBefore: '<div class="remove-me" contenteditable="true">[c1}{c1]<br></div>',
            afterCreate: (peerInfos) => {
                const editor = peerInfos.c1.editor;
                const target = editor.editable.querySelector(".remove-me");
                target.classList.remove("remove-me");
                addStep(editor);
                execCommand(editor, "historyUndo");
                execCommand(editor, "historyRedo");
            },
            contentAfter:
                '<div class="o-paragraph o-we-hint" contenteditable="true" o-we-hint-text="Type &quot;/&quot; for commands">[c1}{c1]<br></div>',
        });
    });
    test("should not sanitize the content of an element recursively when sanitizing an attribute", async () => {
        await testMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: "<div class='content' data-oe-protected='true'><p>base</p></div>",
            afterCreate: (peerInfos) => {
                const editor1 = peerInfos.c1.editor;
                const editor2 = peerInfos.c2.editor;
                const content1 = editor1.editable.querySelector(".content");
                const content2 = editor2.editable.querySelector(".content");
                content2.append(
                    ...parseHTML(
                        editor2.document,
                        "<p>mysecretcode</p><script>secretStuff?.();</script>"
                    ).children
                );
                editor2.editable.append(
                    ...parseHTML(editor2.document, "<p>sanitycheckc2</p>").children
                );
                addStep(editor2);
                content1.setAttribute("onclick", "javascript:badStuff?.()");
                content1.setAttribute("data-info", "43");
                editor1.editable.prepend(
                    ...parseHTML(editor1.document, "<p>sanitycheckc1</p>").children
                );
                addStep(editor1);
                mergePeersSteps(peerInfos);
                // peer 1:
                // did not receive the secret code doing secret stuff from peer 2 because
                // it was protected
                // still has its own onclick attribute doing bad stuff, because he wrote it
                // himself
                expect(peerInfos.c1.editor.editable).toHaveInnerHTML(
                    unformat(`
                        <p>sanitycheckc1</p>
                        <div class="content" data-oe-protected="true" contenteditable="false" onclick="javascript:badStuff?.()" data-info="43">
                            <p>base</p>
                        </div>
                        <p>sanitycheckc2</p>
                    `)
                );
                // peer 2:
                // did not receive the onclick attribute doing bad stuff from peer 1 (was
                // sanitized)
                // received the `data-info="43"` from peer 1, and doing so did not sanitize
                // the custom script doing secret stuff
                expect(peerInfos.c2.editor.editable).toHaveInnerHTML(
                    unformat(`
                        <p>sanitycheckc1</p>
                        <div class="content" data-oe-protected="true" contenteditable="false" data-info="43">
                            <p>base</p>
                            <p>mysecretcode</p>
                            <script>secretStuff?.();</script>
                        </div>
                        <p>sanitycheckc2</p>
                    `)
                );
            },
        });
    });
});
describe("selection", () => {
    test("should rectify a selection offset after an external step", async () => {
        const peerInfos = await setupMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: `<p>a[c1}{c1][c2}{c2]</p>`,
        });
        const e1 = peerInfos.c1.editor;
        e1.shared.dom.insert(parseHTML(e1.document, `<span contenteditable="false">a</span>`));
        e1.shared.history.addStep();
        mergePeersSteps(peerInfos);
        const e2 = peerInfos.c2.editor;
        expect(getContent(e1.editable)).toBe(`<p>a<span contenteditable="false">a</span>[]</p>`);
        expect(getContent(e2.editable)).toBe(`<p>a[]<span contenteditable="false">a</span></p>`);
        const p = e2.editable.querySelector("p");
        e2.shared.selection.setSelection({
            anchorNode: p,
            anchorOffset: 2,
            focusNode: p,
            focusOffset: 2,
        });
        deleteBackward(e2);
        mergePeersSteps(peerInfos);
        expect(getContent(e1.editable)).toBe("<p>a[]</p>");
        expect(getContent(e2.editable)).toBe("<p>a[]</p>");
    });
});
describe("data-oe-protected", () => {
    test("should not share protected mutations and share unprotected ones", async () => {
        await testMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: "<p>[c1}{c1][c2}{c2]<br></p>",
            afterCreate: (peerInfos) => {
                peerInfos.c1.editor.editable.prepend(
                    ...parseHTML(
                        peerInfos.c1.editor.document,
                        unformat(`
                        <div data-oe-protected="true">
                            <p id="true"><br></p>
                            <div data-oe-protected="false">
                                <p id="false"><br></p>
                            </div>
                        </div>
                    `)
                    ).children
                );
                addStep(peerInfos.c1.editor);
                const pTrue = peerInfos.c1.editor.editable.querySelector("#true");
                peerInfos.c1.editor.shared.selection.setSelection({
                    anchorNode: pTrue,
                    anchorOffset: 0,
                });
                pTrue.prepend(peerInfos.c1.editor.document.createTextNode("a"));
                addStep(peerInfos.c1.editor);
                const pFalse = peerInfos.c1.editor.editable.querySelector("#false");
                peerInfos.c1.editor.shared.selection.setSelection({
                    anchorNode: pFalse,
                    anchorOffset: 0,
                });
                insert(peerInfos.c1.editor, "a");
                peerInfos.c2.collaborationPlugin.onExternalHistorySteps(
                    peerInfos.c1.historyPlugin.steps
                );
                validateSameHistory(peerInfos);
            },
            afterCursorInserted: async (peerInfos) => {
                await animationFrame();
                expect(getContent(peerInfos.c1.editor.editable, { sortAttrs: true })).toBe(
                    unformat(`
                        <p data-selection-placeholder=""><br></p>
                        <div contenteditable="false" data-oe-protected="true">
                            <p id="true">a<br></p>
                            <div contenteditable="true" data-oe-protected="false">
                                <p id="false">a[][c1}{c1]</p>
                            </div>
                        </div>
                        <p>[c2}{c2]<br></p>
                    `)
                );
                expect(getContent(peerInfos.c2.editor.editable, { sortAttrs: true })).toBe(
                    unformat(`
                        <p data-selection-placeholder=""><br></p>
                        <div contenteditable="false" data-oe-protected="true">
                            <p id="true"><br></p>
                            <div contenteditable="true" data-oe-protected="false">
                                <p id="false">a[c1}{c1]</p>
                            </div>
                        </div>
                        <p>[][c2}{c2]<br></p>
                    `)
                );
            },
        });
    });

    test("should properly apply `contenteditable` attribute on received protected nodes", async () => {
        const peerInfos = await setupMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: `<p>[c1}{c1][c2}{c2]a</p>`,
        });
        const e1 = peerInfos.c1.editor;
        const e2 = peerInfos.c2.editor;
        e1.shared.dom.insert(
            parseHTML(
                e1.document,
                unformat(`
                    <div data-oe-protected="true">
                        <div data-oe-protected="false">
                            <p>d</p>
                        </div>
                    </div>
                `)
            )
        );
        e1.shared.history.addStep();
        mergePeersSteps(peerInfos);
        expect(getContent(e1.editable, { sortAttrs: true })).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <div contenteditable="false" data-oe-protected="true">
                    <div contenteditable="true" data-oe-protected="false">
                        <p>d</p>
                    </div>
                </div>
                <p>[]a</p>
            `)
        );
        expect(getContent(e2.editable, { sortAttrs: true })).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <div contenteditable="false" data-oe-protected="true">
                    <div contenteditable="true" data-oe-protected="false">
                        <p>d</p>
                    </div>
                </div>
                <p>[]a</p>
            `)
        );
    });
});
describe("serialize/unserialize", () => {
    test("Should add a new node that contain an existing node", async () => {
        const peerInfos = await setupMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: "<p>x</p>",
        });
        applyConcurrentActions(peerInfos, {
            c1: (editor) => {
                const divA = editor.document.createElement("div");
                divA.textContent = "a";
                editor.editable.append(divA);
                const p = editor.editable.querySelector("p:not([data-selection-placeholder])");
                divA.append(p);
                editor.shared.history.addStep();
            },
        });
        mergePeersSteps(peerInfos);
        validateSameHistory(peerInfos);
        validateContent(
            peerInfos,
            '<p data-selection-placeholder=""><br></p><div>a<p>x</p></div><p data-selection-placeholder=""><br></p>'
        );
    });
    test("Should add a new node that contain another node created in the same mutation stack", async () => {
        const peerInfos = await setupMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: "<p>x</p>",
        });
        applyConcurrentActions(peerInfos, {
            c1: (editor) => {
                const divA = editor.document.createElement("div");
                divA.textContent = "a";
                editor.editable.append(divA);
                const divB = editor.document.createElement("div");
                divB.textContent = "b";
                editor.editable.append(divB);
                divB.append(divA);
                editor.shared.history.addStep();
            },
        });
        mergePeersSteps(peerInfos);
        validateSameHistory(peerInfos);
        validateContent(
            peerInfos,
            `<p>x</p><div>b<div class="o-paragraph">a</div></div><p data-selection-placeholder=""><br></p>`
        );
    });
});

describe("Collaboration with embedded components", () => {
    test("should send an empty embedded element", async () => {
        const peerInfos = await setupMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: "<p>[c1}{c1][c2}{c2]<br></p>",
            Plugins: [EmbeddedComponentPlugin],
            resources: {
                embedded_components: [embedding("counter", Counter)],
            },
        });
        const e1 = peerInfos.c1.editor;
        const e2 = peerInfos.c2.editor;
        e1.shared.dom.insert(
            parseHTML(
                e1.document,
                unformat(`
                    <div data-embedded="counter">
                        <p>secret</p>
                    </div>`)
            )
        );
        addStep(e1);
        peerInfos.c2.collaborationPlugin.onExternalHistorySteps(peerInfos.c1.historyPlugin.steps);
        validateSameHistory(peerInfos);
        cleanHints(e2);
        expect(getContent(e2.editable, { sortAttrs: true })).toBe(
            `<p data-selection-placeholder=""><br></p><div contenteditable="false" data-embedded="counter" data-oe-protected="true"></div><p>[]<br></p>`
        );
        await animationFrame();
        cleanHints(e1);
        cleanHints(e2);
        expect(getContent(e1.editable, { sortAttrs: true })).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <div contenteditable="false" data-embedded="counter" data-oe-protected="true">
                    <span class="counter">Counter:0</span>
                </div>
                <p>[]<br></p>
            `)
        );
        expect(getContent(e2.editable, { sortAttrs: true })).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <div contenteditable="false" data-embedded="counter" data-oe-protected="true">
                    <span class="counter">Counter:0</span>
                </div>
                <p>[]<br></p>
            `)
        );
    });

    test("components are mounted and destroyed during addExternalStep", async () => {
        let index = 1;
        patchWithCleanup(Counter.prototype, {
            setup() {
                super.setup();
                this.index = index++;
                onMounted(() => {
                    expect.step(`${this.index} mounted`);
                });
                onWillDestroy(() => {
                    expect.step(`${this.index} destroyed`);
                });
            },
        });
        const peerInfos = await setupMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: `<p>a[c1}{c1][c2}{c2]</p>`,
            Plugins: [EmbeddedComponentPlugin],
            resources: {
                embedded_components: [embedding("counter", Counter)],
            },
        });
        const e1 = peerInfos.c1.editor;
        const e2 = peerInfos.c2.editor;
        e1.shared.dom.insert(parseHTML(e1.document, `<span data-embedded="counter"></span>`));
        e1.shared.history.addStep();
        mergePeersSteps(peerInfos);
        await animationFrame();
        expect.verifySteps(["1 mounted", "2 mounted"]);
        expect(getContent(e1.editable, { sortAttrs: true })).toBe(
            `<p>a<span contenteditable="false" data-embedded="counter" data-oe-protected="true"><span class="counter">Counter:0</span></span>[]</p>`
        );
        expect(getContent(e2.editable, { sortAttrs: true })).toBe(
            `<p>a[]<span contenteditable="false" data-embedded="counter" data-oe-protected="true"><span class="counter">Counter:0</span></span></p>`
        );
        await click(e2.editable.querySelector(".counter"));
        await animationFrame();
        // e1 counter was not clicked, no change
        expect(getContent(e1.editable, { sortAttrs: true })).toBe(
            `<p>a<span contenteditable="false" data-embedded="counter" data-oe-protected="true"><span class="counter">Counter:0</span></span>[]</p>`
        );
        // e2 counter was incremented
        expect(getContent(e2.editable, { sortAttrs: true })).toBe(
            `<p>a[]<span contenteditable="false" data-embedded="counter" data-oe-protected="true"><span class="counter">Counter:1</span></span></p>`
        );
        const p = e2.editable.querySelector("p");
        e2.shared.selection.setSelection({
            anchorNode: p,
            anchorOffset: 2,
            focusNode: p,
            focusOffset: 2,
        });
        deleteBackward(e2);
        mergePeersSteps(peerInfos);
        expect.verifySteps(["2 destroyed", "1 destroyed"]);
    });

    test("components are mounted and destroyed during resetFromSteps", async () => {
        let index = 1;
        patchWithCleanup(Counter.prototype, {
            setup() {
                super.setup();
                this.index = index++;
                onMounted(() => {
                    expect.step(`${this.index} mounted`);
                });
                onWillDestroy(() => {
                    expect.step(`${this.index} destroyed`);
                });
            },
        });
        const peerInfos = await setupMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: `<p>a[c1}{c1][c2}{c2]</p>`,
            Plugins: [EmbeddedComponentPlugin],
            resources: {
                embedded_components: [embedding("counter", Counter)],
            },
        });
        const e1 = peerInfos.c1.editor;
        const e2 = peerInfos.c2.editor;
        e1.shared.dom.insert(parseHTML(e1.document, `<span data-embedded="counter"></span>`));
        e1.shared.history.addStep();
        await animationFrame();
        e2.shared.dom.insert(parseHTML(e2.document, `<span data-embedded="counter"></span>`));
        e2.shared.history.addStep();
        await animationFrame();
        e2.shared.dom.insert(parseHTML(e2.document, `<span data-embedded="counter"></span>`));
        e2.shared.history.addStep();
        await animationFrame();
        expect.verifySteps(["1 mounted", "2 mounted", "3 mounted"]);
        expect(getContent(e1.editable, { sortAttrs: true })).toBe(
            `<p>a<span contenteditable="false" data-embedded="counter" data-oe-protected="true"><span class="counter">Counter:0</span></span>[]</p>`
        );
        expect(getContent(e2.editable, { sortAttrs: true })).toBe(
            unformat(
                `<p>a
                    <span contenteditable="false" data-embedded="counter" data-oe-protected="true"><span class="counter">Counter:0</span></span>
                    <span contenteditable="false" data-embedded="counter" data-oe-protected="true"><span class="counter">Counter:0</span></span>
                []</p>`
            )
        );
        const { steps } = peerInfos.c1.collaborationPlugin.getSnapshotSteps();
        peerInfos.c2.collaborationPlugin.resetFromSteps(steps);
        const p = e2.editable.querySelector("p");
        e2.shared.selection.setSelection({ anchorNode: p, anchorOffset: 0 });
        expect.verifySteps(["2 destroyed", "3 destroyed"]);
        await animationFrame();
        expect.verifySteps(["4 mounted"]);
        expect(getContent(e2.editable, { sortAttrs: true })).toBe(
            `<p>[]a<span contenteditable="false" data-embedded="counter" data-oe-protected="true"><span class="counter">Counter:0</span></span></p>`
        );
        e1.destroy();
        e2.destroy();
        expect.verifySteps(["1 destroyed", "4 destroyed"]);
    });

    test("editableDescendants for components are collaborative (during mount)", async () => {
        const peerInfos = await setupMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: `<p>[c1}{c1][c2}{c2]a</p>`,
            Plugins: [EmbeddedComponentPlugin],
            resources: {
                embedded_components: [
                    embedding("wrapper", EmbeddedWrapper, (host) => ({ host }), {
                        getEditableDescendants,
                    }),
                ],
            },
        });
        const e1 = peerInfos.c1.editor;
        const e2 = peerInfos.c2.editor;
        e1.shared.dom.insert(
            parseHTML(
                e1.document,
                unformat(`
                    <div data-embedded="wrapper">
                        <div data-embedded-editable="deep">
                            <p>deep</p>
                        </div>
                    </div>
                `)
            )
        );
        e1.shared.history.addStep();
        const deep1 = e1.editable.querySelector("[data-embedded-editable='deep'] > p");
        deep1.append(e1.document.createTextNode("1"));
        e1.shared.history.addStep();
        mergePeersSteps(peerInfos);
        const deep2 = e2.editable.querySelector("[data-embedded-editable='deep'] > p");
        deep2.append(e2.document.createTextNode("2"));
        e2.shared.history.addStep();
        mergePeersSteps(peerInfos);
        // Before mount:
        let editable = unformat(`
            <p data-selection-placeholder=""><br></p>
            <div contenteditable="false" data-embedded="wrapper" data-oe-protected="true">
                <div contenteditable="true" data-embedded-editable="deep" data-oe-protected="false">
                    <p>deep12</p>
                </div>
            </div>
            <p>[]a</p>
        `);
        expect(getContent(e1.editable, { sortAttrs: true })).toBe(editable);
        expect(getContent(e2.editable, { sortAttrs: true })).toBe(editable);
        await animationFrame();
        // After mount:
        editable = unformat(`
            <p data-selection-placeholder=""><br></p>
            <div contenteditable="false" data-embedded="wrapper" data-oe-protected="true">
                <div>
                    <div class="deep">
                        <div contenteditable="true" data-embedded-editable="deep" data-oe-protected="false">
                            <p>deep12</p>
                        </div>
                    </div>
                </div>
            </div>
            <p>[]a</p>
        `);
        expect(getContent(e1.editable, { sortAttrs: true })).toBe(editable);
        expect(getContent(e2.editable, { sortAttrs: true })).toBe(editable);
        deep1.append(e1.document.createTextNode("3"));
        e1.shared.history.addStep();
        mergePeersSteps(peerInfos);
        deep2.append(e2.document.createTextNode("4"));
        e2.shared.history.addStep();
        mergePeersSteps(peerInfos);
        editable = unformat(`
            <p data-selection-placeholder=""><br></p>
            <div contenteditable="false" data-embedded="wrapper" data-oe-protected="true">
                <div>
                    <div class="deep">
                        <div contenteditable="true" data-embedded-editable="deep" data-oe-protected="false">
                            <p>deep1234</p>
                        </div>
                    </div>
                </div>
            </div>
            <p>[]a</p>
        `);
        expect(getContent(e1.editable, { sortAttrs: true })).toBe(editable);
        expect(getContent(e2.editable, { sortAttrs: true })).toBe(editable);
    });

    test("editableDescendants for components are collaborative (with different template shapes)", async () => {
        const wrappers = [];
        patchWithCleanup(EmbeddedWrapper.prototype, {
            setup() {
                super.setup();
                wrappers.push(this);
            },
        });
        const peerInfos = await setupMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: `<p>[c1}{c1][c2}{c2]a</p>`,
            Plugins: [EmbeddedComponentPlugin],
            resources: {
                embedded_components: [
                    embedding("wrapper", EmbeddedWrapper, (host) => ({ host }), {
                        getEditableDescendants,
                    }),
                ],
            },
        });
        const e1 = peerInfos.c1.editor;
        const e2 = peerInfos.c2.editor;
        e1.shared.dom.insert(
            parseHTML(
                e1.document,
                unformat(`
                    <div data-embedded="wrapper">
                        <div data-embedded-editable="deep">
                            <p>deep</p>
                        </div>
                    </div>
                `)
            )
        );
        e1.shared.history.addStep();
        // ensure wrappers[0] is for c1
        await animationFrame();
        mergePeersSteps(peerInfos);
        // ensure wrappers[1] is for c2
        await animationFrame();
        const deep1 = e1.editable.querySelector("[data-embedded-editable='deep'] > p");
        const deep2 = e2.editable.querySelector("[data-embedded-editable='deep'] > p");
        // change state for c1
        wrappers[0].state.switch = true;
        deep1.append(e1.document.createTextNode("1"));
        e1.shared.history.addStep();
        // wait for patch for c1
        await animationFrame();
        mergePeersSteps(peerInfos);
        deep2.append(e2.document.createTextNode("2"));
        e2.shared.history.addStep();
        mergePeersSteps(peerInfos);
        expect(getContent(e1.editable, { sortAttrs: true })).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <div contenteditable="false" data-embedded="wrapper" data-oe-protected="true">
                    <div>
                        <div class="switched">
                            <div class="deep">
                                <div contenteditable="true" data-embedded-editable="deep" data-oe-protected="false">
                                    <p>deep12</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <p>[]a</p>
            `)
        );
        expect(getContent(e2.editable, { sortAttrs: true })).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <div contenteditable="false" data-embedded="wrapper" data-oe-protected="true">
                    <div>
                        <div class="deep">
                            <div contenteditable="true" data-embedded-editable="deep" data-oe-protected="false">
                                <p>deep12</p>
                            </div>
                        </div>
                    </div>
                </div>
                <p>[]a</p>
            `)
        );
    });

    test("editableDescendants for components are collaborative (after delete + undo)", async () => {
        const SimpleEmbeddedWrapper = EmbeddedWrapperMixin("deep");
        const peerInfos = await setupMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: `<p>[c1}{c1][c2}{c2]a</p>`,
            Plugins: [EmbeddedComponentPlugin],
            resources: {
                embedded_components: [
                    embedding("wrapper", SimpleEmbeddedWrapper, (host) => ({ host }), {
                        getEditableDescendants,
                    }),
                ],
            },
        });
        const e1 = peerInfos.c1.editor;
        const e2 = peerInfos.c2.editor;
        e1.shared.dom.insert(
            parseHTML(
                e1.document,
                unformat(`
                    <div data-embedded="wrapper">
                        <div data-embedded-editable="deep">
                            <p>deep</p>
                        </div>
                    </div>
                `)
            )
        );
        e1.shared.history.addStep();
        mergePeersSteps(peerInfos);
        await animationFrame();
        deleteBackward(e1);
        mergePeersSteps(peerInfos);
        expect(getContent(e1.editable, { sortAttrs: true })).toBe(`<p>[]a</p>`);
        expect(getContent(e2.editable, { sortAttrs: true })).toBe(`<p>[]a</p>`);
        undo(e1);
        const deep1 = e1.editable.querySelector("[data-embedded-editable='deep'] > p");
        deep1.append(e1.document.createTextNode("1"));
        e1.shared.history.addStep();
        mergePeersSteps(peerInfos);
        await animationFrame();
        const deep2 = e2.editable.querySelector("[data-embedded-editable='deep'] > p");
        deep2.append(e2.document.createTextNode("2"));
        e2.shared.history.addStep();
        mergePeersSteps(peerInfos);
        const editable = unformat(`
            <p data-selection-placeholder=""><br></p>
            <div contenteditable="false" data-embedded="wrapper" data-oe-protected="true">
                <div class="deep">
                    <div contenteditable="true" data-embedded-editable="deep" data-oe-protected="false">
                        <p>deep12</p>
                    </div>
                </div>
            </div>
            <p>[]a</p>
        `);
        expect(getContent(e1.editable, { sortAttrs: true })).toBe(editable);
        expect(getContent(e2.editable, { sortAttrs: true })).toBe(editable);
    });

    test("editableDescendants for components are collaborative (inside a nested component)", async () => {
        const SimpleEmbeddedWrapper = EmbeddedWrapperMixin("deep");
        const peerInfos = await setupMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: `<p>[c1}{c1][c2}{c2]a</p>`,
            Plugins: [EmbeddedComponentPlugin],
            resources: {
                embedded_components: [
                    embedding("wrapper", SimpleEmbeddedWrapper, (host) => ({ host }), {
                        getEditableDescendants,
                    }),
                ],
            },
        });
        const e1 = peerInfos.c1.editor;
        const e2 = peerInfos.c2.editor;
        e1.shared.dom.insert(
            parseHTML(
                e1.document,
                unformat(`
                    <div data-embedded="wrapper">
                        <div data-embedded-editable="deep">
                            <p>shallow</p>
                            <div data-embedded="wrapper">
                                <div data-embedded-editable="deep">
                                    <p>deep</p>
                                </div>
                            </div>
                        </div>
                    </div>
                `)
            )
        );
        e1.shared.history.addStep();
        mergePeersSteps(peerInfos);
        const shallow1 = e1.editable.querySelector("[data-embedded-editable='deep'] > p");
        shallow1.append(e1.document.createTextNode("1"));
        e1.shared.history.addStep();
        const deep1 = e1.editable.querySelectorAll("[data-embedded-editable='deep'] > p")[1];
        deep1.append(e1.document.createTextNode("9"));
        e1.shared.history.addStep();
        await animationFrame();
        mergePeersSteps(peerInfos);
        const shallow2 = e2.editable.querySelector("[data-embedded-editable='deep'] > p");
        shallow2.append(e2.document.createTextNode("2"));
        e2.shared.history.addStep();
        const deep2 = e2.editable.querySelectorAll("[data-embedded-editable='deep'] > p")[1];
        deep2.append(e2.document.createTextNode("8"));
        e2.shared.history.addStep();
        mergePeersSteps(peerInfos);
        const editable = unformat(`
            <p data-selection-placeholder=""><br></p>
            <div contenteditable="false" data-embedded="wrapper" data-oe-protected="true">
                <div class="deep">
                    <div contenteditable="true" data-embedded-editable="deep" data-oe-protected="false">
                        <p>shallow12</p>
                        <div contenteditable="false" data-embedded="wrapper" data-oe-protected="true">
                            <div class="deep">
                                <div contenteditable="true" data-embedded-editable="deep" data-oe-protected="false">
                                    <p>deep98</p>
                                </div>
                            </div>
                        </div>
                        <p data-selection-placeholder=""><br></p>
                    </div>
                </div>
            </div>
            <p>[]a</p>
        `);
        expect(getContent(e1.editable, { sortAttrs: true })).toBe(editable);
        expect(getContent(e2.editable, { sortAttrs: true })).toBe(editable);
    });

    describe("Embedded state", () => {
        beforeEach(() => {
            let id = 1;
            patchWithCleanup(StateChangeManager.prototype, {
                generateId: () => id++,
            });
        });

        test("A peer change to the embedded state is properly applied for every other collaborator", async () => {
            const peerInfos = await setupMultiEditor({
                peerIds: ["c1", "c2"],
                contentBefore: `<p>a[c1}{c1][c2}{c2]<span data-embedded="counter" data-embedded-props='{"value":1}'></span></p>`,
                Plugins: [EmbeddedComponentPlugin],
                resources: {
                    embedded_components: [savedCounter],
                },
            });
            const e1 = peerInfos.c1.editor;
            const e2 = peerInfos.c2.editor;
            const counter1 = [...peerInfos.c1.plugins.get("embeddedComponents").components][0].root
                .node.component;
            const counter2 = [...peerInfos.c2.plugins.get("embeddedComponents").components][0].root
                .node.component;
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"value":1}' data-oe-protected="true"><span class="counter">Counter:1</span></span></p>`
            );
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"value":1}' data-oe-protected="true"><span class="counter">Counter:1</span></span></p>`
            );
            counter1.embeddedState.value = 3;
            await animationFrame();
            mergePeersSteps(peerInfos);
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"value":3}' data-embedded-state='{"stateChangeId":1,"previous":{"value":1},"next":{"value":3}}' data-oe-protected="true"><span class="counter">Counter:3</span></span></p>`
            );
            await animationFrame();
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"value":3}' data-embedded-state='{"stateChangeId":1,"previous":{"value":1},"next":{"value":3}}' data-oe-protected="true"><span class="counter">Counter:3</span></span></p>`
            );
            expect(counter2.embeddedState).toEqual({
                value: 3,
            });
            counter2.embeddedState.value = 5;
            await animationFrame();
            mergePeersSteps(peerInfos);
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"value":5}' data-embedded-state='{"stateChangeId":2,"previous":{"value":3},"next":{"value":5}}' data-oe-protected="true"><span class="counter">Counter:5</span></span></p>`
            );
            await animationFrame();
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"value":5}' data-embedded-state='{"stateChangeId":2,"previous":{"value":3},"next":{"value":5}}' data-oe-protected="true"><span class="counter">Counter:5</span></span></p>`
            );
            expect(counter1.embeddedState).toEqual({
                value: 5,
            });
        });

        test("Undo and Redo can overwrite a collaborator changes to the embedded state", async () => {
            // Undo and Redo can be confusing with states. The idea is that a step is "owned" by
            // a collaborator, and the current peer can not undo it. Instead, the history allows the
            // peer to undo his own last step. In summary:
            // - undo for peer goes from the current state (which can be set by the collaborator)
            // to the state before his own last step.
            // - redo for peer goes from the current state (which can be set by the collaborator)
            // to the state before his own last undo.
            const peerInfos = await setupMultiEditor({
                peerIds: ["c1", "c2"],
                contentBefore: `<p>a[c1}{c1][c2}{c2]<span data-embedded="counter" data-embedded-props='{"value":1}'></span></p>`,
                Plugins: [EmbeddedComponentPlugin],
                resources: {
                    embedded_components: [savedCounter],
                },
            });
            const e1 = peerInfos.c1.editor;
            const e2 = peerInfos.c2.editor;
            const counter1 = [...peerInfos.c1.plugins.get("embeddedComponents").components][0].root
                .node.component;
            const counter2 = [...peerInfos.c2.plugins.get("embeddedComponents").components][0].root
                .node.component;
            counter2.embeddedState.value = 2;
            await animationFrame();
            mergePeersSteps(peerInfos);
            await animationFrame();
            counter1.embeddedState.value = 3;
            await animationFrame();
            mergePeersSteps(peerInfos);
            await animationFrame();
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"value":3}' data-embedded-state='{"stateChangeId":2,"previous":{"value":2},"next":{"value":3}}' data-oe-protected="true"><span class="counter">Counter:3</span></span></p>`
            );
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"value":3}' data-embedded-state='{"stateChangeId":2,"previous":{"value":2},"next":{"value":3}}' data-oe-protected="true"><span class="counter">Counter:3</span></span></p>`
            );
            // e2 last step was to go from 1 to 2. e2 can not undo step from e1
            // therefore undo does 3 -> 1
            undo(e2);
            await animationFrame();
            mergePeersSteps(peerInfos);
            await animationFrame();
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"value":1}' data-embedded-state='{"stateChangeId":3,"previous":{"value":3},"next":{"value":1}}' data-oe-protected="true"><span class="counter">Counter:1</span></span></p>`
            );
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"value":1}' data-embedded-state='{"stateChangeId":3,"previous":{"value":3},"next":{"value":1}}' data-oe-protected="true"><span class="counter">Counter:1</span></span></p>`
            );
            // e1 last step was to go from 2 to 3. e1 can not undo step from e2
            // therefore undo does 1 -> 2
            undo(e1);
            await animationFrame();
            mergePeersSteps(peerInfos);
            await animationFrame();
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"value":2}' data-embedded-state='{"stateChangeId":4,"previous":{"value":1},"next":{"value":2}}' data-oe-protected="true"><span class="counter">Counter:2</span></span></p>`
            );
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"value":2}' data-embedded-state='{"stateChangeId":4,"previous":{"value":1},"next":{"value":2}}' data-oe-protected="true"><span class="counter">Counter:2</span></span></p>`
            );
            // e2 last undo was to go from 3 -> 1. e2 can not redo step from e1
            // therefore redo does 2 -> 3
            redo(e2);
            await animationFrame();
            mergePeersSteps(peerInfos);
            await animationFrame();
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"value":3}' data-embedded-state='{"stateChangeId":5,"previous":{"value":2},"next":{"value":3}}' data-oe-protected="true"><span class="counter">Counter:3</span></span></p>`
            );
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"value":3}' data-embedded-state='{"stateChangeId":5,"previous":{"value":2},"next":{"value":3}}' data-oe-protected="true"><span class="counter">Counter:3</span></span></p>`
            );
            // e1 last undo was to go from 1 -> 2. redo does 3 -> 1.
            redo(e1);
            await animationFrame();
            mergePeersSteps(peerInfos);
            await animationFrame();
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"value":1}' data-embedded-state='{"stateChangeId":6,"previous":{"value":3},"next":{"value":1}}' data-oe-protected="true"><span class="counter">Counter:1</span></span></p>`
            );
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"value":1}' data-embedded-state='{"stateChangeId":6,"previous":{"value":3},"next":{"value":1}}' data-oe-protected="true"><span class="counter">Counter:1</span></span></p>`
            );
        });

        test("Restoring a savePoint from makeSavePoint maintains collaborators changes to the embedded state", async () => {
            const peerInfos = await setupMultiEditor({
                peerIds: ["c1", "c2"],
                contentBefore: `<p>a[c1}{c1][c2}{c2]</p><div data-embedded="obj" data-embedded-props='{"obj":{"1":1}}'></div>`,
                Plugins: [EmbeddedComponentPlugin],
                resources: {
                    embedded_components: [collaborativeObject],
                },
            });
            const e1 = peerInfos.c1.editor;
            const e2 = peerInfos.c2.editor;
            const obj1 = [...peerInfos.c1.plugins.get("embeddedComponents").components][0].root.node
                .component;
            const obj2 = [...peerInfos.c2.plugins.get("embeddedComponents").components][0].root.node
                .component;
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>a[]</p><div contenteditable="false" data-embedded="obj" data-embedded-props='{"obj":{"1":1}}' data-oe-protected="true"><div class="obj">1_1</div></div><p data-selection-placeholder=""><br></p>`
            );
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a[]</p><div contenteditable="false" data-embedded="obj" data-embedded-props='{"obj":{"1":1}}' data-oe-protected="true"><div class="obj">1_1</div></div><p data-selection-placeholder=""><br></p>`
            );
            obj2.embeddedState.obj["2"] = 2;
            await animationFrame();
            mergePeersSteps(peerInfos);
            await animationFrame();
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>a[]</p><div contenteditable="false" data-embedded="obj" data-embedded-props='{"obj":{"1":1,"2":2}}' data-embedded-state='{"stateChangeId":1,"previous":{"obj":{"1":1}},"next":{"obj":{"1":1,"2":2}}}' data-oe-protected="true"><div class="obj">1_1,2_2</div></div><p data-selection-placeholder=""><br></p>`
            );
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a[]</p><div contenteditable="false" data-embedded="obj" data-embedded-props='{"obj":{"1":1,"2":2}}' data-embedded-state='{"stateChangeId":1,"previous":{"obj":{"1":1}},"next":{"obj":{"1":1,"2":2}}}' data-oe-protected="true"><div class="obj">1_1,2_2</div></div><p data-selection-placeholder=""><br></p>`
            );
            const savepoint = e1.shared.history.makeSavePoint();
            delete obj2.embeddedState.obj["1"];
            await animationFrame();
            mergePeersSteps(peerInfos);
            await animationFrame();
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>a[]</p><div contenteditable="false" data-embedded="obj" data-embedded-props='{"obj":{"2":2}}' data-embedded-state='{"stateChangeId":2,"previous":{"obj":{"1":1,"2":2}},"next":{"obj":{"2":2}}}' data-oe-protected="true"><div class="obj">2_2</div></div><p data-selection-placeholder=""><br></p>`
            );
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a[]</p><div contenteditable="false" data-embedded="obj" data-embedded-props='{"obj":{"2":2}}' data-embedded-state='{"stateChangeId":2,"previous":{"obj":{"1":1,"2":2}},"next":{"obj":{"2":2}}}' data-oe-protected="true"><div class="obj">2_2</div></div><p data-selection-placeholder=""><br></p>`
            );
            obj1.embeddedState.obj["3"] = 3;
            await animationFrame();
            mergePeersSteps(peerInfos);
            await animationFrame();
            obj2.embeddedState.obj["4"] = 4;
            await animationFrame();
            mergePeersSteps(peerInfos);
            await animationFrame();
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>a[]</p><div contenteditable="false" data-embedded="obj" data-embedded-props='{"obj":{"2":2,"3":3,"4":4}}' data-embedded-state='{"stateChangeId":4,"previous":{"obj":{"2":2,"3":3}},"next":{"obj":{"2":2,"3":3,"4":4}}}' data-oe-protected="true"><div class="obj">2_2,3_3,4_4</div></div><p data-selection-placeholder=""><br></p>`
            );
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a[]</p><div contenteditable="false" data-embedded="obj" data-embedded-props='{"obj":{"2":2,"3":3,"4":4}}' data-embedded-state='{"stateChangeId":4,"previous":{"obj":{"2":2,"3":3}},"next":{"obj":{"2":2,"3":3,"4":4}}}' data-oe-protected="true"><div class="obj">2_2,3_3,4_4</div></div><p data-selection-placeholder=""><br></p>`
            );
            savepoint();
            await animationFrame();
            mergePeersSteps(peerInfos);
            await animationFrame();
            // 3, which was added after makeSavePoint, was removed from obj
            // for every collaborator after the savepoint restoration.
            // stateChangeId evolves from 4 to 9 because steps 2,3,4 were
            // reverted, and only steps 2 and 4 were applied again, 3 was
            // not re-applied since it was done by c1. The last applied state
            // change is the transition from {2} to {2, 4}, but the step
            // generated by the savePoint contains all state changes from
            // {2, 3, 4} to {2, 4}, and that is why it is applied correctly
            // for both users.
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>a[]</p><div contenteditable="false" data-embedded="obj" data-embedded-props='{"obj":{"2":2,"4":4}}' data-embedded-state='{"stateChangeId":9,"previous":{"obj":{"2":2}},"next":{"obj":{"2":2,"4":4}}}' data-oe-protected="true"><div class="obj">2_2,4_4</div></div><p data-selection-placeholder=""><br></p>`
            );
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a[]</p><div contenteditable="false" data-embedded="obj" data-embedded-props='{"obj":{"2":2,"4":4}}' data-embedded-state='{"stateChangeId":9,"previous":{"obj":{"2":2}},"next":{"obj":{"2":2,"4":4}}}' data-oe-protected="true"><div class="obj">2_2,4_4</div></div><p data-selection-placeholder=""><br></p>`
            );
        });

        test("New component with an embedded state received from a collaborator can have its state when it hasn't finished being mounted", async () => {
            const peerInfos = await setupMultiEditor({
                peerIds: ["c1", "c2"],
                contentBefore: `<p>a[c1}{c1][c2}{c2]</p>`,
                Plugins: [EmbeddedComponentPlugin],
                resources: {
                    embedded_components: [savedCounter],
                },
            });
            const e1 = peerInfos.c1.editor;
            const e2 = peerInfos.c2.editor;
            e2.shared.dom.insert(
                parseHTML(
                    e2.document,
                    `<span data-embedded="counter" data-embedded-props='{"value":1}'></span>`
                )
            );
            e2.shared.history.addStep();
            await animationFrame();
            const counter2 = [...peerInfos.c2.plugins.get("embeddedComponents").components][0].root
                .node.component;
            counter2.embeddedState.value = 3;
            await animationFrame();
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a<span contenteditable="false" data-embedded="counter" data-embedded-props='{"value":3}' data-embedded-state='{"stateChangeId":1,"previous":{"value":1},"next":{"value":3}}' data-oe-protected="true"><span class="counter">Counter:3</span></span>[]</p>`
            );
            insert(e1, "bc");
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(`<p>abc[]</p>`);
            mergePeersSteps(peerInfos);
            await animationFrame();
            // TODO @phoenix: selection should be at the end of the span for e2,
            // but it was not correctly updated after external steps. To update
            // when the selection is properly handled in collaboration.
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>abc[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"value":3}' data-embedded-state='{"stateChangeId":1,"previous":{"value":1},"next":{"value":3}}' data-oe-protected="true"><span class="counter">Counter:3</span></span></p>`
            );
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>abc[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"value":3}' data-embedded-state='{"stateChangeId":1,"previous":{"value":1},"next":{"value":3}}' data-oe-protected="true"><span class="counter">Counter:3</span></span></p>`
            );
        });

        test("Late embedded state changes received from a collaborator are properly applied on a mounted component", async () => {
            const peerInfos = await setupMultiEditor({
                peerIds: ["c1", "c2"],
                contentBefore: `<p>a[c1}{c1][c2}{c2]</p><div data-embedded="obj" data-embedded-props='{"obj":{"1":1}}'></div>`,
                Plugins: [EmbeddedComponentPlugin],
                resources: {
                    embedded_components: [collaborativeObject],
                },
            });
            const e1 = peerInfos.c1.editor;
            const e2 = peerInfos.c2.editor;
            const obj1 = [...peerInfos.c1.plugins.get("embeddedComponents").components][0].root.node
                .component;
            const obj2 = [...peerInfos.c2.plugins.get("embeddedComponents").components][0].root.node
                .component;
            obj1.embeddedState.obj["2"] = 2;
            obj1.embeddedState.obj["3"] = 4;
            obj2.embeddedState.obj["3"] = 3;
            obj2.embeddedState.obj["4"] = 4;
            await animationFrame();
            mergePeersSteps(peerInfos);
            await animationFrame();
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>a[]</p><div contenteditable="false" data-embedded="obj" data-embedded-props='{"obj":{"1":1,"2":2,"3":3,"4":4}}' data-embedded-state='{"stateChangeId":2,"previous":{"obj":{"1":1}},"next":{"obj":{"1":1,"3":3,"4":4}}}' data-oe-protected="true"><div class="obj">1_1,2_2,3_3,4_4</div></div><p data-selection-placeholder=""><br></p>`
            );
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a[]</p><div contenteditable="false" data-embedded="obj" data-embedded-props='{"obj":{"1":1,"2":2,"3":3,"4":4}}' data-embedded-state='{"stateChangeId":2,"previous":{"obj":{"1":1}},"next":{"obj":{"1":1,"3":3,"4":4}}}' data-oe-protected="true"><div class="obj">1_1,2_2,3_3,4_4</div></div><p data-selection-placeholder=""><br></p>`
            );
            undo(e2);
            await animationFrame();
            mergePeersSteps(peerInfos);
            await animationFrame();
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>a[]</p><div contenteditable="false" data-embedded="obj" data-embedded-props='{"obj":{"1":1,"2":2}}' data-embedded-state='{"stateChangeId":3,"previous":{"obj":{"1":1,"2":2,"3":3,"4":4}},"next":{"obj":{"1":1,"2":2}}}' data-oe-protected="true"><div class="obj">1_1,2_2</div></div><p data-selection-placeholder=""><br></p>`
            );
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a[]</p><div contenteditable="false" data-embedded="obj" data-embedded-props='{"obj":{"1":1,"2":2}}' data-embedded-state='{"stateChangeId":3,"previous":{"obj":{"1":1,"2":2,"3":3,"4":4}},"next":{"obj":{"1":1,"2":2}}}' data-oe-protected="true"><div class="obj">1_1,2_2</div></div><p data-selection-placeholder=""><br></p>`
            );
        });

        test("Late embedded state changes received from a collaborator are properly applied on a destroyed component", async () => {
            const peerInfos = await setupMultiEditor({
                peerIds: ["c1", "c2"],
                contentBefore: `<p>a[c1}{c1][c2}{c2]</p><div data-embedded="obj" data-embedded-props='{"obj":{"1":1}}'></div>`,
                Plugins: [EmbeddedComponentPlugin],
                resources: {
                    embedded_components: [collaborativeObject],
                },
            });
            const e1 = peerInfos.c1.editor;
            const e2 = peerInfos.c2.editor;
            const obj1 = [...peerInfos.c1.plugins.get("embeddedComponents").components][0].root.node
                .component;
            const obj2 = [...peerInfos.c2.plugins.get("embeddedComponents").components][0].root.node
                .component;
            obj1.embeddedState.obj["2"] = 2;
            obj2.embeddedState.obj["3"] = 3;
            await animationFrame();
            deleteForward(e2);
            mergePeersSteps(peerInfos);
            await animationFrame();
            undo(e2);
            mergePeersSteps(peerInfos);
            await animationFrame();
            // When steps were merged, both users updated their state with
            // both changes, even if the component was outside of the dom.
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>a[]</p><div contenteditable="false" data-embedded="obj" data-embedded-props='{"obj":{"1":1,"2":2,"3":3}}' data-embedded-state='{"stateChangeId":2,"previous":{"obj":{"1":1}},"next":{"obj":{"1":1,"3":3}}}' data-oe-protected="true"><div class="obj">1_1,2_2,3_3</div></div><p data-selection-placeholder=""><br></p>`
            );
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a[]</p><div contenteditable="false" data-embedded="obj" data-embedded-props='{"obj":{"1":1,"2":2,"3":3}}' data-embedded-state='{"stateChangeId":2,"previous":{"obj":{"1":1}},"next":{"obj":{"1":1,"3":3}}}' data-oe-protected="true"><div class="obj">1_1,2_2,3_3</div></div><p data-selection-placeholder=""><br></p>`
            );
        });

        test("Collaborative state changes can be applied while a current change is still pending", async () => {
            const peerInfos = await setupMultiEditor({
                peerIds: ["c1", "c2"],
                contentBefore: `<p>a[c1}{c1][c2}{c2]<span data-embedded="counter" data-embedded-props='{"value":1}'></span></p>`,
                Plugins: [EmbeddedComponentPlugin],
                resources: {
                    embedded_components: [savedCounter],
                },
            });
            const e1 = peerInfos.c1.editor;
            const e2 = peerInfos.c2.editor;
            const counter1 = [...peerInfos.c1.plugins.get("embeddedComponents").components][0].root
                .node.component;
            const counter2 = [...peerInfos.c2.plugins.get("embeddedComponents").components][0].root
                .node.component;
            counter2.embeddedState.value = 2;
            await animationFrame();
            counter1.embeddedState.value = 3;
            mergePeersSteps(peerInfos);
            await animationFrame();
            // c1 change was not yet shared with c2 since it was pending
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"value":2}' data-embedded-state='{"stateChangeId":1,"previous":{"value":1},"next":{"value":2}}' data-oe-protected="true"><span class="counter">Counter:2</span></span></p>`
            );
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"value":3}' data-embedded-state='{"stateChangeId":2,"previous":{"value":2},"next":{"value":3}}' data-oe-protected="true"><span class="counter">Counter:3</span></span></p>`
            );
            // share the missing step with c2
            mergePeersSteps(peerInfos);
            await animationFrame();
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"value":3}' data-embedded-state='{"stateChangeId":2,"previous":{"value":2},"next":{"value":3}}' data-oe-protected="true"><span class="counter">Counter:3</span></span></p>`
            );
        });

        test("A pending change applied after collaborative changes only update modified properties of that change (other properties are left untouched)", async () => {
            class NamedCounter extends SavedCounter {
                static template = xml`
                    <span class="counter" t-on-click="increment"><t t-esc="embeddedState.name"/>:<t t-esc="counterValue"/></span>`;
            }
            const namedCounter = {
                ...savedCounter,
                Component: NamedCounter,
            };
            const peerInfos = await setupMultiEditor({
                peerIds: ["c1", "c2"],
                contentBefore: `<p>a[c1}{c1][c2}{c2]<span data-embedded="counter" data-embedded-props='{"name":"unnamed","value":1}'></span></p>`,
                Plugins: [EmbeddedComponentPlugin],
                resources: {
                    embedded_components: [namedCounter],
                },
            });
            const e1 = peerInfos.c1.editor;
            const e2 = peerInfos.c2.editor;
            const counter1 = [...peerInfos.c1.plugins.get("embeddedComponents").components][0].root
                .node.component;
            const counter2 = [...peerInfos.c2.plugins.get("embeddedComponents").components][0].root
                .node.component;
            counter1.embeddedState.name = "newName";
            await animationFrame();
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"name":"newName","value":1}' data-embedded-state='{"stateChangeId":1,"previous":{"name":"unnamed","value":1},"next":{"name":"newName","value":1}}' data-oe-protected="true"><span class="counter">newName:1</span></span></p>`
            );
            counter2.embeddedState.value = 2;
            mergePeersSteps(peerInfos);
            await animationFrame();
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"name":"newName","value":1}' data-embedded-state='{"stateChangeId":1,"previous":{"name":"unnamed","value":1},"next":{"name":"newName","value":1}}' data-oe-protected="true"><span class="counter">newName:1</span></span></p>`
            );
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"name":"newName","value":2}' data-embedded-state='{"stateChangeId":2,"previous":{"name":"newName","value":1},"next":{"name":"newName","value":2}}' data-oe-protected="true"><span class="counter">newName:2</span></span></p>`
            );
            mergePeersSteps(peerInfos);
            await animationFrame();
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"name":"newName","value":2}' data-embedded-state='{"stateChangeId":2,"previous":{"name":"newName","value":1},"next":{"name":"newName","value":2}}' data-oe-protected="true"><span class="counter">newName:2</span></span></p>`
            );
        });

        test("Collaborative state changes received late can be applied while a current change is still pending", async () => {
            const peerInfos = await setupMultiEditor({
                peerIds: ["c1", "c2"],
                contentBefore: `<p>a[c1}{c1][c2}{c2]<span data-embedded="counter" data-embedded-props='{"value":1}'></span></p>`,
                Plugins: [EmbeddedComponentPlugin],
                resources: {
                    embedded_components: [savedCounter],
                },
            });
            const e1 = peerInfos.c1.editor;
            const e2 = peerInfos.c2.editor;
            const counter1 = [...peerInfos.c1.plugins.get("embeddedComponents").components][0].root
                .node.component;
            const counter2 = [...peerInfos.c2.plugins.get("embeddedComponents").components][0].root
                .node.component;
            counter2.embeddedState.value = 2;
            counter1.embeddedState.value = 3;
            await animationFrame();
            counter1.embeddedState.value = 4;
            mergePeersSteps(peerInfos);
            await animationFrame();
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"value":2}' data-embedded-state='{"stateChangeId":1,"previous":{"value":1},"next":{"value":2}}' data-oe-protected="true"><span class="counter">Counter:2</span></span></p>`
            );
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"value":4}' data-embedded-state='{"stateChangeId":3,"previous":{"value":2},"next":{"value":4}}' data-oe-protected="true"><span class="counter">Counter:4</span></span></p>`
            );
            mergePeersSteps(peerInfos);
            await animationFrame();
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"value":4}' data-embedded-state='{"stateChangeId":3,"previous":{"value":2},"next":{"value":4}}' data-oe-protected="true"><span class="counter">Counter:4</span></span></p>`
            );
        });

        test("State changes are properly un-applied in the context of makeSavePoint even on a destroyed component", async () => {
            const peerInfos = await setupMultiEditor({
                peerIds: ["c1", "c2"],
                contentBefore: `<p>a[c1}{c1][c2}{c2]</p><div data-embedded="obj" data-embedded-props='{"obj":{"1":1}}'></div>`,
                Plugins: [EmbeddedComponentPlugin],
                resources: {
                    embedded_components: [collaborativeObject],
                },
            });
            const e1 = peerInfos.c1.editor;
            const e2 = peerInfos.c2.editor;
            const obj1 = [...peerInfos.c1.plugins.get("embeddedComponents").components][0].root.node
                .component;
            const savepoint = e1.shared.history.makeSavePoint();
            obj1.embeddedState.obj["2"] = 2;
            await animationFrame();
            mergePeersSteps(peerInfos);
            await animationFrame();
            deleteForward(e2);
            mergePeersSteps(peerInfos);
            savepoint();
            mergePeersSteps(peerInfos);
            undo(e2);
            mergePeersSteps(peerInfos);
            await animationFrame();
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>a[]</p><div contenteditable="false" data-embedded="obj" data-embedded-props='{"obj":{"1":1}}' data-embedded-state='{"stateChangeId":2,"previous":{"obj":{"1":1,"2":2}},"next":{"obj":{"1":1}}}' data-oe-protected="true"><div class="obj">1_1</div></div><p data-selection-placeholder=""><br></p>`
            );
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a[]</p><div contenteditable="false" data-embedded="obj" data-embedded-props='{"obj":{"1":1}}' data-embedded-state='{"stateChangeId":2,"previous":{"obj":{"1":1,"2":2}},"next":{"obj":{"1":1}}}' data-oe-protected="true"><div class="obj">1_1</div></div><p data-selection-placeholder=""><br></p>`
            );
        });

        test("A change from a collaborator with the same values as the previous change done by the peer is properly applied", async () => {
            const peerInfos = await setupMultiEditor({
                peerIds: ["c1", "c2"],
                contentBefore: `<p>a[c1}{c1][c2}{c2]<span data-embedded="counter" data-embedded-props='{"baseValue":1}'></span></p>`,
                Plugins: [EmbeddedComponentPlugin],
                resources: {
                    embedded_components: [offsetCounter],
                },
            });
            const e1 = peerInfos.c1.editor;
            const e2 = peerInfos.c2.editor;
            const counter1 = [...peerInfos.c1.plugins.get("embeddedComponents").components][0].root
                .node.component;
            const counter2 = [...peerInfos.c2.plugins.get("embeddedComponents").components][0].root
                .node.component;
            counter1.embeddedState.baseValue = 3;
            counter2.embeddedState.baseValue = 3;
            await animationFrame();
            mergePeersSteps(peerInfos);
            await animationFrame();
            // for the offsetCounter, baseValue is updated with the difference
            // between previous and next. So if both users made a change going
            // from 1 to 3, the resulting value should be 5.
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"baseValue":5}' data-embedded-state='{"stateChangeId":2,"previous":{"baseValue":1},"next":{"baseValue":3}}' data-oe-protected="true"><span class="counter">Counter:5</span></span></p>`
            );
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"baseValue":5}' data-embedded-state='{"stateChangeId":2,"previous":{"baseValue":1},"next":{"baseValue":3}}' data-oe-protected="true"><span class="counter">Counter:5</span></span></p>`
            );
            undo(e1);
            await animationFrame();
            mergePeersSteps(peerInfos);
            await animationFrame();
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"baseValue":3}' data-embedded-state='{"stateChangeId":3,"previous":{"baseValue":5},"next":{"baseValue":3}}' data-oe-protected="true"><span class="counter">Counter:3</span></span></p>`
            );
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>a[]<span contenteditable="false" data-embedded="counter" data-embedded-props='{"baseValue":3}' data-embedded-state='{"stateChangeId":3,"previous":{"baseValue":5},"next":{"baseValue":3}}' data-oe-protected="true"><span class="counter">Counter:3</span></span></p>`
            );
        });

        test("Reverting the insertion of the first key in a collaborative object does not remove the object if it does not become empty", async () => {
            const peerInfos = await setupMultiEditor({
                peerIds: ["c1", "c2"],
                contentBefore: `<p>a[c1}{c1][c2}{c2]</p><div data-embedded="obj"></div>`,
                Plugins: [EmbeddedComponentPlugin],
                resources: {
                    embedded_components: [collaborativeObject],
                },
            });
            const e1 = peerInfos.c1.editor;
            const e2 = peerInfos.c2.editor;
            const obj1 = [...peerInfos.c1.plugins.get("embeddedComponents").components][0].root.node
                .component;
            const obj2 = [...peerInfos.c2.plugins.get("embeddedComponents").components][0].root.node
                .component;
            obj1.embeddedState.obj = {};
            obj1.embeddedState.obj["1"] = 1;
            await animationFrame();
            mergePeersSteps(peerInfos);
            await animationFrame();
            obj2.embeddedState.obj["2"] = 2;
            await animationFrame();
            mergePeersSteps(peerInfos);
            await animationFrame();
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>a[]</p><div contenteditable="false" data-embedded="obj" data-embedded-props='{"obj":{"1":1,"2":2}}' data-embedded-state='{"stateChangeId":2,"previous":{"obj":{"1":1}},"next":{"obj":{"1":1,"2":2}}}' data-oe-protected="true"><div class="obj">1_1,2_2</div></div><p data-selection-placeholder=""><br></p>`
            );
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a[]</p><div contenteditable="false" data-embedded="obj" data-embedded-props='{"obj":{"1":1,"2":2}}' data-embedded-state='{"stateChangeId":2,"previous":{"obj":{"1":1}},"next":{"obj":{"1":1,"2":2}}}' data-oe-protected="true"><div class="obj">1_1,2_2</div></div><p data-selection-placeholder=""><br></p>`
            );
            undo(e1);
            await animationFrame();
            mergePeersSteps(peerInfos);
            await animationFrame();
            expect(getContent(e1.editable, { sortAttrs: true })).toBe(
                `<p>a[]</p><div contenteditable="false" data-embedded="obj" data-embedded-props='{"obj":{"2":2}}' data-embedded-state='{"stateChangeId":3,"previous":{"obj":{"1":1,"2":2}},"next":{"obj":{"2":2}}}' data-oe-protected="true"><div class="obj">2_2</div></div><p data-selection-placeholder=""><br></p>`
            );
            expect(getContent(e2.editable, { sortAttrs: true })).toBe(
                `<p>a[]</p><div contenteditable="false" data-embedded="obj" data-embedded-props='{"obj":{"2":2}}' data-embedded-state='{"stateChangeId":3,"previous":{"obj":{"1":1,"2":2}},"next":{"obj":{"2":2}}}' data-oe-protected="true"><div class="obj">2_2</div></div><p data-selection-placeholder=""><br></p>`
            );
        });
    });

    test("Should not duplicate selection placeholders", async () => {
        const peerInfos = await setupMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: '<p>a[c1}{c1][c2}{c2]</p><div data-embedded="obj"></div>',
            Plugins: [EmbeddedComponentPlugin],
            resources: {
                embedded_components: [collaborativeObject],
            },
        });
        const e1 = peerInfos.c1.editor;
        const e2 = peerInfos.c2.editor;
        const contentBefore =
            '<p>a[]</p><div data-embedded="obj" data-oe-protected="true" contenteditable="false"><div class="obj"></div></div>' +
            '<p data-selection-placeholder=""><br></p>';
        await animationFrame();
        expect(getContent(e1.editable)).toBe(contentBefore);
        expect(getContent(e2.editable)).toBe(contentBefore);
        e1.shared.dom.insert("b");
        addStep(e1);
        await animationFrame();
        expect(getContent(e1.editable)).toBe(contentBefore.replace("a[]", "ab[]"));
        expect(getContent(e2.editable)).toBe(contentBefore);
        await animationFrame();
        mergePeersSteps(peerInfos);
        expect(getContent(e1.editable)).toBe(contentBefore.replace("a[]", "ab[]"));
        expect(getContent(e2.editable)).toBe(contentBefore.replace("a[]", "a[]b"));
    });
});

test("Should not duplicate selection placeholders", async () => {
    const peerInfos = await setupMultiEditor({
        peerIds: ["c1", "c2"],
        contentBefore: '<p>a[c1}{c1][c2}{c2]</p><div contenteditable="false">c</div>',
    });
    const e1 = peerInfos.c1.editor;
    const e2 = peerInfos.c2.editor;
    const contentBefore =
        '<p>a[]</p><div contenteditable="false">c</div>' +
        '<p data-selection-placeholder=""><br></p>';
    expect(getContent(e1.editable)).toBe(contentBefore);
    expect(getContent(e2.editable)).toBe(contentBefore);
    e1.shared.dom.insert("b");
    addStep(e1);
    expect(getContent(e1.editable)).toBe(contentBefore.replace("a[]", "ab[]"));
    expect(getContent(e2.editable)).toBe(contentBefore);
    await animationFrame();
    mergePeersSteps(peerInfos);
    expect(getContent(e1.editable)).toBe(contentBefore.replace("a[]", "ab[]"));
    expect(getContent(e2.editable)).toBe(contentBefore.replace("a[]", "a[]b"));
});
