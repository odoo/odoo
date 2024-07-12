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

async function testFindPosition({ previous, next, extraSetup }) {
    const { editor, el } = await setupEditor(previous);
    extraSetup?.(editor, el);

    let [node, offset] = findAdjacentPosition(editor, "forward");
    setSelection({ anchorNode: node, anchorOffset: offset });
    expect(getContent(el)).toBe(next);

    [node, offset] = findAdjacentPosition(editor, "backward");
    setSelection({ anchorNode: node, anchorOffset: offset });
    expect(getContent(el)).toBe(previous);
}

describe("findAdjacentPosition method", () => {
    describe("Basic", () => {
        test("should find adjacent character", async () => {
            await testFindPosition({
                previous: "<p>a[]bcd</p>",
                next: "<p>ab[]cd</p>",
            });
        });
        test("should find adjacent character (2)", async () => {
            await testFindPosition({
                previous: "<p>[]abcd</p>",
                next: "<p>a[]bcd</p>",
            });
        });
        test("should find adjacent character in different text node", async () => {
            await testFindPosition({
                extraSetup: (editor, el) => {
                    const textNode = el.firstChild.firstChild;
                    textNode.splitText(2);
                },
                previous: "<p>a[]bcd</p>",
                next: "<p>ab[]cd</p>",
            });
        });
        test("should find first position after paragraph break", async () => {
            await testFindPosition({
                previous: "<p>ab[]</p><p>cd</p>",
                next: "<p>ab</p><p>[]cd</p>",
            });
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
                await testFindPosition({
                    previous: '<p>a[]<span contenteditable="false">b</span>c</p>',
                    next: '<p>a<span contenteditable="false">b</span>[]c</p>',
                });
            });
            test("Should find position after paragraph break", async () => {
                await testFindPosition({
                    previous: '<div><p>a[]</p><span contenteditable="false">b</span></div>',
                    next: '<div><p>a</p>[]<span contenteditable="false">b</span></div>',
                });
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
            await testFindPosition({
                previous: unformat(`
                    <div contenteditable="false">
                        <p>abc</p>
                        <p contenteditable="true">[]def</p>
                    </div>
                    <p>fgh</p>
                `),
                next: unformat(`
                    <div contenteditable="false">
                        <p>abc</p>
                        <p contenteditable="true">d[]ef</p>
                    </div>
                    <p>fgh</p>
                `),
            });
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
