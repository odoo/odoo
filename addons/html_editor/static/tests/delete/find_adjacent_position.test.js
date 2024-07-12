import { describe, expect, test } from "@odoo/hoot";
import { setupEditor } from "../_helpers/editor";
import { getContent, setSelection } from "../_helpers/selection";
import { unformat } from "../_helpers/format";

function findAdjacentPosition(editor, direction) {
    const deletePlugin = editor.plugins.find((p) => p.constructor.name === "delete");
    const selection = editor.document.getSelection();
    const { anchorNode, anchorOffset } = selection;

    return deletePlugin.findAdjacentPosition(anchorNode, anchorOffset, direction);
}

function assertAdjacentPositions(editor, previous, next) {
    let [node, offset] = findAdjacentPosition(editor, "forward");
    setSelection({ anchorNode: node, anchorOffset: offset });
    expect(getContent(editor.editable)).toBe(next);

    [node, offset] = findAdjacentPosition(editor, "backward");
    setSelection({ anchorNode: node, anchorOffset: offset });
    expect(getContent(editor.editable)).toBe(previous);
}

describe("findAdjacentPosition method", () => {
    describe("Basic", () => {
        test("should find adjacent character", async () => {
            const previous = "<p>a[]bcd</p>";
            const next = "<p>ab[]cd</p>";
            const { editor } = await setupEditor(previous);
            assertAdjacentPositions(editor, previous, next);
        });
        test("should find adjacent character (2)", async () => {
            const previous = "<p>[]abcd</p>";
            const next = "<p>a[]bcd</p>";
            const { editor } = await setupEditor(previous);
            assertAdjacentPositions(editor, previous, next);
        });
        test("should find adjacent character in different text node", async () => {
            const previous = "<p>a[]bcd</p>";
            const next = "<p>ab[]cd</p>";
            const { editor, el } = await setupEditor(previous);
            // Split text node between 'a' and 'b'
            const textNode = el.firstChild.firstChild;
            textNode.splitText(1);
            setSelection({ anchorNode: textNode, anchorOffset: 1 });
            assertAdjacentPositions(editor, previous, next);
        });
        test("should find first position after paragraph break", async () => {
            const previous = "<p>ab[]</p><p>cd</p>";
            const next = "<p>ab</p><p>[]cd</p>";
            const { editor } = await setupEditor(previous);
            assertAdjacentPositions(editor, previous, next);
        });
        test("should not find anything before the first position", async () => {
            const { editor } = await setupEditor("<p>[]abc</p>");
            const [node, offset] = findAdjacentPosition(editor, "backward");
            expect(node).toBe(null);
            expect(offset).toBe(null);
        });
        test("should not find anything after the last position", async () => {
            const { editor } = await setupEditor("<p>abc[]</p>");
            const [node, offset] = findAdjacentPosition(editor, "forward");
            expect(node).toBe(null);
            expect(offset).toBe(null);
        });
        test("should skip invisible character", async () => {
            const { editor, el } = await setupEditor("<p>d[]\u200bef</p>");
            const [node, offset] = findAdjacentPosition(editor, "forward");
            setSelection({ anchorNode: node, anchorOffset: offset });
            expect(getContent(el)).toBe("<p>d\u200be[]f</p>");
            // @todo: non-reversible operation (e.g. backward results in
            // <p>d\u200b[]ef</p>). Should it be?
        });
        test("should skip invisible character (2)", async () => {
            const { editor, el } = await setupEditor("<p>d\u200b[]ef</p>");
            const [node, offset] = findAdjacentPosition(editor, "backward");
            setSelection({ anchorNode: node, anchorOffset: offset });
            expect(getContent(el)).toBe("<p>[]d\u200bef</p>");
        });
    });
    describe("Contenteditable=false elements", () => {
        describe("Inlines", () => {
            test("Should find position after the span", async () => {
                const previous = '<p>a[]<span contenteditable="false">b</span>c</p>';
                const next = '<p>a<span contenteditable="false">b</span>[]c</p>';
                const { editor } = await setupEditor(previous);
                assertAdjacentPositions(editor, previous, next);
            });
            test("Should find position after paragraph break", async () => {
                const previous = '<div><p>a[]</p><span contenteditable="false">b</span></div>';
                const next = '<div><p>a</p>[]<span contenteditable="false">b</span></div>';
                const { editor } = await setupEditor(previous);
                assertAdjacentPositions(editor, previous, next);
            });
        });
        describe("Blocks", () => {
            test("Should find position after the div", async () => {
                const { editor, el } = await setupEditor(
                    '<p>a[]</p><div contenteditable="false">b</div><p>c</p>'
                );
                const [node, offset] = findAdjacentPosition(editor, "forward");
                setSelection({ anchorNode: node, anchorOffset: offset });
                expect(getContent(el)).toBe(
                    // This position is not reachable with the keyboard, but
                    // it's the desirable one to compose a range for deletion,
                    // allowing to remove the div with deleteForward without
                    // afecting the paragraph after it.
                    '<p>a</p><div contenteditable="false">b</div>[]<p>c</p>'
                );
            });
            test("Should find position before the div", async () => {
                const { editor, el } = await setupEditor(
                    '<p>a</p><div contenteditable="false">b</div><p>[]c</p>'
                );
                const [node, offset] = findAdjacentPosition(editor, "backward");
                setSelection({ anchorNode: node, anchorOffset: offset });
                expect(getContent(el)).toBe(
                    // This position is not reachable with the keyboard, but
                    // it's the desirable one to compose a range for deletion,
                    // allowing to remove the div with deleteBackward without
                    // afecting the paragraph before it.
                    '<p>a</p>[]<div contenteditable="false">b</div><p>c</p>'
                );
            });
        });
    });
    describe("Different editable zones", () => {
        test("should find adjacent character", async () => {
            const previous = unformat(`
                <div contenteditable="false">
                    <p>abc</p>
                    <p contenteditable="true">[]def</p>
                </div>
                <p>fgh</p>
            `);
            const next = unformat(`
                <div contenteditable="false">
                    <p>abc</p>
                    <p contenteditable="true">d[]ef</p>
                </div>
                <p>fgh</p>
            `);
            const { editor } = await setupEditor(previous);
            assertAdjacentPositions(editor, previous, next);
        });
        test("should not find anything outside the closest editable root", async () => {
            const { editor } = await setupEditor(
                unformat(`
                    <div contenteditable="false">
                        <p>abc</p>
                        <p contenteditable="true">[]def</p>
                    </div>
                    <p>fgh</p>
                `)
            );
            const [node, offset] = findAdjacentPosition(editor, "backward");
            expect(node).toBe(null);
            expect(offset).toBe(null);
        });
        test("should not find anything outside the closest editable root (2)", async () => {
            const { editor } = await setupEditor(
                unformat(`
                    <div contenteditable="false">
                        <p>abc</p>
                        <p contenteditable="true">def[]</p>
                    </div>
                    <p>fgh</p>
                `)
            );
            const [node, offset] = findAdjacentPosition(editor, "forward");
            expect(node).toBe(null);
            expect(offset).toBe(null);
        });
        test("Should find position before the div", async () => {
            const { editor, el } = await setupEditor(
                unformat(`
                    <div contenteditable="false">
                        <p>abc</p>
                        <p contenteditable="true">def</p>
                    </div>
                    <p>[]fgh</p>
                `)
            );
            const [node, offset] = findAdjacentPosition(editor, "backward");
            setSelection({ anchorNode: node, anchorOffset: offset });
            expect(getContent(el)).toBe(
                // This position is not reachable with the keyboard, but
                // it's the desirable one to compose a range for deletion,
                // allowing to remove the div with deleteBackward
                unformat(`
                    []<div contenteditable="false">
                        <p>abc</p>
                        <p contenteditable="true">def</p>
                    </div>
                    <p>fgh</p>
                `)
            );
        });
        test("Should find position after the div", async () => {
            const { editor, el } = await setupEditor(
                unformat(`
                    <p>fgh[]</p>
                    <div contenteditable="false">
                        <p>abc</p>
                        <p contenteditable="true">def</p>
                    </div>
                `)
            );
            const [node, offset] = findAdjacentPosition(editor, "forward");
            setSelection({ anchorNode: node, anchorOffset: offset });
            expect(getContent(el)).toBe(
                // This position is not reachable with the keyboard, but
                // it's the desirable one to compose a range for deletion,
                // allowing to remove the div with deleteForward
                unformat(`
                    <p>fgh</p>
                    <div contenteditable="false">
                        <p>abc</p>
                        <p contenteditable="true">def</p>
                    </div>[]
                `)
            );
        });
    });
});
