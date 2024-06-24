import { describe, expect, test } from "@odoo/hoot";
import { Deferred } from "@web/core/utils/concurrency";
import { Plugin } from "@html_editor/plugin";
import { parseHTML } from "@html_editor/utils/html";
import { unformat } from "./_helpers/format";
import { addStep, undo } from "./_helpers/user_actions";
import {
    applyConcurrentActions,
    mergePeersSteps,
    setupMultiEditor,
    testMultiEditor,
    validateSameHistory,
    validateContent,
    renderTextualSelection,
} from "./_helpers/collaboration";
import { animationFrame } from "@odoo/hoot-mock";

/**
 * @param {Editor} editor
 * @param {string} value
 */
function insert(editor, value) {
    editor.shared.domInsert(value);
    editor.dispatch("ADD_STEP");
}
/**
 * @param {Editor} editor
 */
function deleteBackward(editor) {
    editor.dispatch("DELETE_BACKWARD");
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
            expect(peerInfos.c1.editor.editable.innerHTML).toBe("<p><x>a</x><y>bd</y></p>", {
                message: "error with peer c1",
            });
            expect(peerInfos.c2.editor.editable.innerHTML).toBe("<p><x>ac</x><y>b</y></p>", {
                message: "error with peer c2",
            });
        },
    });
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
            expect(peerInfos.c2.historyPlugin.steps[0].mutations.map((x) => x.id)).toEqual([
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
    test("should sanitize when adding a node", async () => {
        await testMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: "<p><x>a</x></p>",
            afterCreate: (peerInfos) => {
                const script = document.createElement("script");
                script.innerHTML = 'console.log("xss")';
                peerInfos.c1.editor.editable.append(script);
                addStep(peerInfos.c1.editor);
                expect(peerInfos.c1.historyPlugin.steps[1]).not.toBe(undefined);
                peerInfos.c2.collaborationPlugin.onExternalHistorySteps([
                    peerInfos.c1.historyPlugin.steps[1],
                ]);
                expect(peerInfos.c2.editor.editable.innerHTML).toBe("<p><x>a</x></p>");
            },
        });
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
                expect(peerInfos.c2.editor.editable.innerHTML).toBe(
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
                img.setAttribute("onerror", 'console.log("xss")');
                addStep(peerInfos.c1.editor);
                peerInfos.c2.collaborationPlugin.onExternalHistorySteps([
                    peerInfos.c1.historyPlugin.steps[1],
                ]);
                expect(peerInfos.c1.editor.editable.innerHTML).toBe(
                    '<p>a<img class="b" onerror="console.log(&quot;xss&quot;)"></p>'
                );
                expect(peerInfos.c2.editor.editable.innerHTML).toBe('<p>a<img class="b"></p>');
            },
        });
    });

    test("should sanitize when undo is adding a script node", async () => {
        await testMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: "<p>a</p>",
            afterCreate: (peerInfos) => {
                const script = document.createElement("script");
                script.innerHTML = 'console.log("xss")';
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
                peerInfos.c2.editor.dispatch("HISTORY_UNDO");
                expect(peerInfos.c2.editor.editable.innerHTML).toBe("<p>a</p>");
            },
        });
    });
    test("should sanitize when undo is adding a descendant script node", async () => {
        await testMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: "<p>a</p>",
            afterCreate: (peerInfos) => {
                const div = document.createElement("div");
                div.innerHTML = '<i>b</i><script>console.log("xss")</script>';
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
                peerInfos.c2.editor.dispatch("HISTORY_UNDO");
                expect(peerInfos.c2.editor.editable.innerHTML).toBe("<p>a</p><div><i>b</i></div>");
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
                img.setAttribute("onerror", 'console.log("xss")');
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
                peerInfos.c2.editor.dispatch("HISTORY_UNDO");
                expect(peerInfos.c2.editor.editable.innerHTML).toBe('<p>a<img class="b"></p>');
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
                editor.dispatch("HISTORY_UNDO");
                editor.dispatch("HISTORY_REDO");
            },
            contentAfter:
                '<div contenteditable="true" placeholder="Type &quot;/&quot; for commands" class="o-we-hint">[c1}{c1]<br></div>',
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
                expect(peerInfos.c1.editor.editable.innerHTML).toBe(
                    unformat(`
                        <p>sanitycheckc1</p>
                        <div class="content" data-oe-protected="true" onclick="javascript:badStuff?.()" data-info="43">
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
                expect(peerInfos.c2.editor.editable.innerHTML).toBe(
                    unformat(`
                        <p>sanitycheckc1</p>
                        <div class="content" data-oe-protected="true" data-info="43">
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
describe("data-oe-protected", () => {
    test("should not share protected mutations and share unprotected ones", async () => {
        await testMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: "<p>[c1}{c1][c2}{c2]</p>",
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
                peerInfos.c1.editor.shared.setSelection({
                    anchorNode: pTrue,
                    anchorOffset: 0,
                });
                pTrue.prepend(peerInfos.c1.editor.document.createTextNode("a"));
                addStep(peerInfos.c1.editor);
                const pFalse = peerInfos.c1.editor.editable.querySelector("#false");
                peerInfos.c1.editor.shared.setSelection({
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
                expect(peerInfos.c1.editor.editable.innerHTML).toBe(
                    unformat(`
                        <div data-oe-protected="true">
                            <p id="true">a<br></p>
                            <div data-oe-protected="false">
                                <p id="false">a[c1}{c1]<br></p>
                            </div>
                        </div>
                        <p>[c2}{c2]</p>
                    `)
                );
                expect(peerInfos.c2.editor.editable.innerHTML).toBe(
                    unformat(`
                        <div data-oe-protected="true">
                            <p id="true"><br></p>
                            <div data-oe-protected="false">
                                <p id="false">a[c1}{c1]<br></p>
                            </div>
                        </div>
                        <p>[c2}{c2]</p>
                    `)
                );
            },
        });
    });
});
describe("data-oe-transient-content", () => {
    test("should send an empty transient-content element", async () => {
        await testMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: "<p>[c1}{c1][c2}{c2]</p>",
            afterCreate: (peerInfos) => {
                peerInfos.c1.editor.editable.prepend(
                    ...parseHTML(
                        peerInfos.c1.editor.document,
                        unformat(`
                        <div data-oe-transient-content="true">
                            <p>secret</p>
                        </div>
                    `)
                    ).children
                );
                addStep(peerInfos.c1.editor);
                peerInfos.c2.collaborationPlugin.onExternalHistorySteps(
                    peerInfos.c1.historyPlugin.steps
                );
                validateSameHistory(peerInfos);
            },
            afterCursorInserted: async (peerInfos) => {
                await animationFrame();
                expect(peerInfos.c1.editor.editable.innerHTML).toBe(
                    unformat(`
                        <div data-oe-transient-content="true">
                            <p>secret</p>
                        </div>
                        <p>[c1}{c1][c2}{c2]</p>
                    `)
                );
                expect(peerInfos.c2.editor.editable.innerHTML).toBe(
                    unformat(`
                        <div data-oe-transient-content="true"></div>
                        <p>[c1}{c1][c2}{c2]</p>
                    `)
                );
            },
        });
    });
});
describe("post process external steps", () => {
    test("should properly await a processing promise before accepting new external steps.", async () => {
        const deferredPromise = new Deferred();
        const postProcessExternalSteps = (element) => {
            if (element.querySelector(".process")) {
                setTimeout(() => {
                    deferredPromise.resolve();
                });
                return deferredPromise;
            }
            return null;
        };
        class ConfigPlugin extends Plugin {
            static name = "collab-test-config";
            static resources = () => ({
                post_process_external_steps: postProcessExternalSteps,
            });
        }
        await testMultiEditor({
            Plugins: [ConfigPlugin],
            peerIds: ["c1", "c2"],
            contentBefore: "<p>a[c1}{c1][c2}{c2]</p>",
            afterCreate: async (peerInfos) => {
                peerInfos.c1.editor.editable.append(
                    ...parseHTML(
                        peerInfos.c1.editor.document,
                        unformat(`
                        <div class="process">
                            <p>secret</p>
                        </div>
                    `)
                    ).children
                );
                addStep(peerInfos.c1.editor);
                peerInfos.c1.editor.editable.append(
                    ...parseHTML(
                        peerInfos.c1.editor.document,
                        unformat(`
                        <p>post-process</p>
                    `)
                    ).children
                );
                addStep(peerInfos.c1.editor);
                peerInfos.c2.collaborationPlugin.onExternalHistorySteps(
                    peerInfos.c1.historyPlugin.steps
                );
                expect(peerInfos.c1.editor.editable.innerHTML).toBe(
                    unformat(`
                        <p>a</p>
                        <div class="process">
                            <p>secret</p>
                        </div>
                        <p>post-process</p>
                    `)
                );
                expect(peerInfos.c2.editor.editable.innerHTML).toBe(
                    unformat(`
                        <p>a</p>
                        <div class="process">
                            <p>secret</p>
                        </div>
                    `)
                );
                await peerInfos.c2.collaborationPlugin.postProcessExternalStepsPromise;
                expect(peerInfos.c2.editor.editable.innerHTML).toBe(
                    unformat(`
                        <p>a</p>
                        <div class="process">
                            <p>secret</p>
                        </div>
                        <p>post-process</p>
                    `)
                );
                validateSameHistory(peerInfos);
            },
        });
    });
});
