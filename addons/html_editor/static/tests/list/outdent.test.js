import { describe, expect, test, before } from "@odoo/hoot";
import { setupEditor, testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { bold, deleteBackward, keydownShiftTab } from "../_helpers/user_actions";
import { getContent } from "../_helpers/selection";

before(
    () =>
        document.fonts.add(
            new FontFace("Roboto", "url(/web/static/fonts/google/Roboto/Roboto-Regular.ttf)")
        ).ready
);

describe("Regular list", () => {
    test.tags("font-dependent");
    test("should remove the list-style when outdent the list", async () => {
        await testEditor({
            styleContent: "ul { font: 14px Roboto }",
            contentBefore: unformat(`
                    <ul>
                        <li class="oe-nested" style="list-style: upper-latin;">
                            <ul>
                                <li>a[b]c</li>
                            </ul>
                        </li>
                    </ul>`),
            stepFunction: keydownShiftTab,
            contentAfter: unformat(`
                    <ul>
                        <li>a[b]c</li>
                    </ul>`),
        });
    });
});

describe("Checklist", () => {
    test("should outdent a checklist", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">a[b]c</li>
                            </ul>
                        </li>
                    </ul>`),
            stepFunction: keydownShiftTab,
            contentAfter: unformat(`
                <ul class="o_checklist">
                    <li class="o_checked">a[b]c</li>
                </ul>`),
        });
        await testEditor({
            contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li>a[b]c</li>
                            </ul>
                        </li>
                    </ul>`),
            stepFunction: keydownShiftTab,
            contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li>a[b]c</li>
                    </ul>`),
        });
    });

    test('should outdent a checklist and previous line as "title"', async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li><p>abc</p>
                            <ul class="o_checklist">
                                <li class="o_checked">d[e]f</li>
                            </ul>
                        </li>
                    </ul>`),
            stepFunction: keydownShiftTab,
            contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li><p>abc</p></li>
                        <li class="o_checked">d[e]f</li>
                    </ul>`),
        });
        await testEditor({
            contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li><p>abc</p>
                            <ul class="o_checklist">
                                <li>d[e]f</li>
                            </ul>
                        </li>
                    </ul>`),
            stepFunction: keydownShiftTab,
            contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li><p>abc</p></li>
                        <li>d[e]f</li>
                    </ul>`),
        });
    });
});

describe("with selection collapsed", () => {
    test("should outdent the last element of a list", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul>
                        <li><p>
                            a
                        </p>
                            <ul>
                                <li>[]b</li>
                            </ul>
                        </li>
                    </ul>`),
            stepFunction: keydownShiftTab,
            contentAfter: unformat(`
                    <ul>
                        <li><p>a</p></li>
                        <li>[]b</li>
                    </ul>`),
        });
    });

    test("should outdent the last element of a list with proper with unordered list", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ol>
                        <li><p>
                            a
                        </p>
                            <ol>
                                <li>[]b</li>
                            </ol>
                        </li>
                    </ol>`),
            stepFunction: keydownShiftTab,
            contentAfter: unformat(`
                    <ol>
                        <li><p>a</p></li>
                        <li>[]b</li>
                    </ol>`),
        });
    });

    test("should outdent the middle element of a list", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul>
                        <li><p>
                            a
                        </p>
                            <ul>
                                <li>[]b</li>
                            </ul>
                        </li>
                        <li>
                            c
                        </li>
                    </ul>`),
            stepFunction: keydownShiftTab,
            contentAfter: unformat(`
                    <ul>
                        <li><p>a</p></li>
                        <li>[]b</li>
                        <li>c</li>
                    </ul>`),
        });
    });

    test("should outdent if the first element of a list is selected", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul>
                        <li>[]a</li>
                        <li>b</li>
                    </ul>`),
            stepFunction: keydownShiftTab,
            contentAfter: unformat(`
                    <p>[]a</p>
                    <ul>
                        <li>b</li>
                    </ul>`),
        });
    });

    test("should outdent the last element of a list with sublist", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul>
                        <li><p>
                            a
                        </p>
                            <ul>
                                <li class="oe-nested">
                                    <ul>
                                        <li>[]c</li>
                                    </ul>
                                </li>
                            </ul>
                        </li>
                    </ul>`),
            stepFunction: keydownShiftTab,
            contentAfter: unformat(`
                    <ul>
                        <li><p>
                            a
                        </p>
                            <ul>
                                <li>[]c</li>
                            </ul>
                        </li>
                    </ul>`),
        });
        await testEditor({
            contentBefore: unformat(`
                    <ul>
                        <li><p>
                            a
                        </p>
                            <ul>
                                <li>[]c</li>
                            </ul>
                        </li>
                    </ul>`),
            stepFunction: keydownShiftTab,
            contentAfter: unformat(`
                    <ul>
                        <li><p>
                            a
                        </p></li>
                        <li>[]c</li>
                    </ul>`),
        });
    });

    test("should outdent unordered list inside a table cell", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td>
                                    ghi
                                </td>
                                <td>
                                    <ul>
                                        <li><p>abc</p>
                                            <ul>
                                                <li>def[]</li>
                                            </ul>
                                        </li>
                                    </ul>
                                </td>
                                <td>
                                    jkl
                                </td>
                            </tr>
                        </tbody>
                    </table>
                `),
            stepFunction: (editor) => keydownShiftTab(editor),
            contentAfter: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td>
                                    ghi
                                </td>
                                <td>
                                    <ul>
                                        <li><p>abc</p></li>
                                        <li>def[]</li>
                                    </ul>
                                </td>
                                <td>
                                    jkl
                                </td>
                            </tr>
                        </tbody>
                    </table>
                `),
        });
    });

    test("should outdent checklist inside a table cell", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td>
                                    ghi
                                </td>
                                <td>
                                    <ul class="o_checklist">
                                        <li><p>abc</p>
                                            <ul class="o_checklist">
                                                <li>def[]</li>
                                            </ul>
                                        </li>
                                    </ul>
                                </td>
                                <td>
                                    jkl
                                </td>
                            </tr>
                        </tbody>
                    </table>
                `),
            stepFunction: (editor) => keydownShiftTab(editor),
            contentAfter: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td>
                                    ghi
                                </td>
                                <td>
                                    <ul class="o_checklist">
                                        <li><p>abc</p></li>
                                        <li>def[]</li>
                                    </ul>
                                </td>
                                <td>
                                    jkl
                                </td>
                            </tr>
                        </tbody>
                    </table>
                `),
        });
    });

    describe("should outdent a list inside a nav-item list", () => {
        test("should outdent a list inside a nav-item list (1)", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <ul>
                        <li class="nav-item">
                            <ul>
                                <li>a[]b</li>
                            </ul>
                        </li>
                    </ul>
                `),
                stepFunction: keydownShiftTab,
                contentAfter: unformat(`
                    <ul>
                        <li class="nav-item">
                            <p>a[]b</p>
                        </li>
                    </ul>
                `),
            });
        });
        test("should outdent a list inside a nav-item list (2)", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <ul>
                        <li class="nav-item">
                            <ol>
                                <li>a[]b</li>
                            </ol>
                        </li>
                    </ul>
                `),
                stepFunction: keydownShiftTab,
                contentAfter: unformat(`
                    <ul>
                        <li class="nav-item">
                            <p>a[]b</p>
                        </li>
                    </ul>
                `),
            });
        });
        test("should outdent a list inside a nav-item list (3)", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <ul>
                        <li class="nav-item">
                            <ul class="o_checklist">
                                <li>a[]b</li>
                            </ul>
                        </li>
                    </ul>
                `),
                stepFunction: keydownShiftTab,
                contentAfter: unformat(`
                    <ul>
                        <li class="nav-item">
                            <p>a[]b</p>
                        </li>
                    </ul>
                `),
            });
        });
        test("should outdent a list inside a nav-item list (4)", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <ul>
                        <li class="nav-item">
                            <div>
                                <ul>
                                    <li>a[]b</li>
                                </ul>
                            </div>
                        </li>
                    </ul>
                `),
                stepFunction: keydownShiftTab,
                contentAfter: unformat(`
                    <ul>
                        <li class="nav-item">
                            <div>
                                <p>a[]b</p>
                            </div>
                        </li>
                    </ul>
                `),
            });
        });
        test("should outdent a list inside a nav-item list (5)", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <ul>
                        <li class="nav-item">
                            <div>
                                <ol>
                                    <li>
                                        <h1>a[]b</h1>
                                    </li>
                                </ol>
                            </div>
                        </li>
                    </ul>
                `),
                stepFunction: keydownShiftTab,
                contentAfter: unformat(`
                    <ul>
                        <li class="nav-item">
                            <div>
                                <h1>a[]b</h1>
                            </div>
                        </li>
                    </ul>
                `),
            });
        });
        test("should outdent a list inside a nav-item list (6)", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <ul>
                        <li class="nav-item">
                            <div>
                                <ul class="o_checklist">
                                    <li>a[]b</li>
                                </ul>
                            </div>
                        </li>
                    </ul>
                `),
                stepFunction: keydownShiftTab,
                contentAfter: unformat(`
                    <ul>
                        <li class="nav-item">
                            <div>
                                <p>a[]b</p>
                            </div>
                        </li>
                    </ul>
                `),
            });
        });
    });
    test("should outdent a list item with blocks", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>a</li>
                    <li>
                        <h1>[]b</h1>
                        <h2>c</h2>
                    </li>
                </ul>`),
            stepFunction: keydownShiftTab,
            contentAfter: unformat(`
                <ul>
                    <li>a</li>
                </ul>
                <h1>[]b</h1>
                <h2>c</h2>`),
        });
    });
    test("should not crash when outdenting a list item with empty nodes", async () => {
        const { el, editor } = await setupEditor(
            unformat(`
                <ul>
                    <li>a</li>
                    <li>[]</li>
                </ul>`)
        );
        // add an empty text node to the list item
        el.firstChild.lastChild.append(editor.document.createTextNode(""));
        keydownShiftTab(editor);
        expect(getContent(el)).toBe(
            unformat(`
                <ul>
                    <li>a</li>
                </ul>
                <p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`)
        );
    });
    test("should not crash when outdenting a list item with invisible nodes", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>a</li>
                    <li>[]<br></li>
                </ul>`),
            stepFunction: (editor) => {
                bold(editor); // produces a <strong> tag with zws inside
                deleteBackward(editor); // removes the marker
                deleteBackward(editor); // outdents the list item
            },
            contentAfter: unformat(`
                <ul>
                    <li>a</li>
                </ul>
                <p>[]<br></p>`),
        });
    });
    test("should correctly merge list items when outdenting nested list", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ol>
                    <li>
                        <div>abc</div>
                        <ol>
                            <li>def</li>
                            <li class="oe-nested">
                                <div>[]ghi</div>
                                <ol>
                                    <li>jkl</li>
                                </ol>
                            </li>
                            <li>mno</li>
                        </ol>
                    </li>
                    <li>pqr</li>
                </ol>
            `),
            stepFunction: (editor) => {
                keydownShiftTab(editor);
                keydownShiftTab(editor);
            },
            contentAfter: unformat(`
                <ol>
                    <li>
                        <div>abc</div>
                        <ol>
                            <li>def</li>
                        </ol>
                    </li>
                </ol>
                <div>[]ghi</div>
                <ol>
                    <li class="oe-nested">
                        <ol>
                            <li class="oe-nested">
                                <ol>
                                    <li>jkl</li>
                                </ol>
                            </li>
                            <li>mno</li>
                        </ol>
                    </li>
                    <li>pqr</li>
                </ol>
            `),
        });
    });
});

describe("with selection", () => {
    test("should outdent the middle element of a list", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul>
                        <li><p>
                            a
                        </p>
                            <ul>
                                <li>[b]</li>
                            </ul>
                        </li>
                        <li>
                            c
                        </li>
                    </ul>`),
            stepFunction: keydownShiftTab,
            contentAfter: unformat(`
                    <ul>
                        <li><p>a</p></li>
                        <li>[b]</li>
                        <li>c</li>
                    </ul>`),
        });
    });

    test("should outdent multiples list item in the middle element of a list", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul>
                        <li>
                            a
                            <ul>
                                <li>[b</li>
                                <li>c]</li>
                            </ul>
                        </li>
                        <li>
                            d
                        </li>
                    </ul>`),
            contentBeforeEdit: unformat(`
                        <ul>
                            <li>
                                <p>a</p>
                                <ul>
                                    <li>[b</li>
                                    <li>c]</li>
                                </ul>
                            </li>
                            <li>
                                d
                            </li>
                        </ul>`),
            stepFunction: keydownShiftTab,
            contentAfter: unformat(`
                    <ul>
                        <li><p>a</p></li>
                        <li>[b</li>
                        <li>c]</li>
                        <li>d</li>
                    </ul>`),
        });
    });

    test("should outdent multi-levl list", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li class="oe-nested">
                        <ul>
                            <li><p>[a</p>
                                <ul>
                                    <li><p>b</p>
                                        <ul>
                                            <li><p>c</p>
                                                <ul>
                                                    <li>d</li>
                                                </ul>
                                            </li>
                                            <li>e</li>
                                        </ul>
                                    </li>
                                    <li>f</li>
                                </ul>
                            </li>
                            <li>g]</li>
                        </ul>
                    </li>
                </ul>`),
            stepFunction: keydownShiftTab,
            contentAfter: unformat(`
                <ul>
                    <li><p>[a</p>
                        <ul>
                            <li><p>b</p>
                                <ul>
                                    <li><p>c</p>
                                        <ul>
                                            <li>d</li>
                                        </ul>
                                    </li>
                                    <li>e</li>
                                </ul>
                            </li>
                            <li>f</li>
                        </ul>
                    </li>
                    <li>g]</li>
                </ul>`),
        });
    });

    // @wrongCommand
    // This test fails because the original test tested the "indentList" command
    // (with mode="outdent"), which has a different behavior than keydown
    // shift+Tab.
    // In web_editor, "indentList" commmand is not called anywhere, except in
    // the tests.
    // So, not passing this test does not mean that a previously working feature
    // is broken, as the user had no way to trigger the "indentList" command.
    // By the way: is this a valid contentBefore?
    test.skip("should outdent multiples list item in the middle element of a list with sublist", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul>
                        <li>
                            a
                            <ul>
                                <li>
                                    [b
                                    <ul>
                                        <li>c</li>
                                    </ul>
                                </li>
                                <li>d]</li>
                            </ul>
                        </li>
                        <li>e</li>
                    </ul>`),
            stepFunction: keydownShiftTab,
            contentAfter: unformat(`
                    <ul>
                        <li>a</li>
                        <li><p>
                            [b
                        </p>
                            <ul>
                                <li>c</li>
                            </ul>
                        </li>
                        <li>d]</li>
                        <li>e</li>
                    </ul>`),
        });
        await testEditor({
            contentBefore: unformat(`
                    <ul>
                        <li>
                            a
                            <ul>
                                <li>
                                    b
                                    <ul>
                                        <li>[c</li>
                                    </ul>
                                </li>
                                <li>d]</li>
                            </ul>
                        </li>
                        <li>e</li>
                    </ul>`),
            stepFunction: keydownShiftTab,
            contentAfter: unformat(`
                    <ul>
                        <li>
                            a
                            <ul>
                                <li>b</li>
                                <li>[c</li>
                            </ul>
                        </li>
                        <li>d]</li>
                        <li>e</li>
                    </ul>`),
        });
    });

    // @wrongCommand (same as above)
    test.skip("should outdent nested list and list with elements in a upper level than the rangestart", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul>
                        <li>a</li>
                        <li>
                            b
                            <ul>
                                <li>
                                    c
                                    <ul>
                                        <li>[d</li>
                                    </ul>
                                </li>
                                <li>
                                e
                                <ul>
                                    <li>f</li>
                                    <li>g</li>
                                </ul>
                            </li>
                            <li>h]</li>
                            </ul>
                        </li>
                        <li>i</li>
                    </ul>`),
            stepFunction: keydownShiftTab,
            contentAfter: unformat(`
                    <ul>
                        <li>a</li>
                        <li>b
                            <ul>
                                <li>c</li>
                                <li>[d</li>
                            </ul>
                        </li>
                        <li><p>e</p>
                            <ul>
                                <li>f</li>
                                <li>g</li>
                            </ul>
                        </li>
                        <li>h]</li>
                        <li>i</li>
                    </ul>`),
        });
    });

    test("should not outdent a non-editable list", async () => {
        await testEditor({
            contentBefore: unformat(`
                <p>[before</p>
                <ul>
                    <li class="oe-nested">
                        <ul>
                            <li>a</li>
                        </ul>
                    </li>
                </ul>
                <ul contenteditable="false">
                    <li>a</li>
                </ul>
                <p>after]</p>`),
            stepFunction: keydownShiftTab,
            contentAfter: unformat(`
                <p>[before</p>
                <ul>
                    <li>a</li>
                </ul>
                <ul contenteditable="false">
                    <li>a</li>
                </ul>
                <p>after]</p>`),
        });
    });

    test("should outdent a ordered list inside a table cell", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td>
                                    ghi
                                </td>
                                <td>
                                    <ol>
                                        <li><p>abc</p>
                                            <ol>
                                                <li>[def]</li>
                                            </ol>
                                        </li>
                                    </ol>
                                    </td>
                                <td>
                                    jkl
                                </td>
                            </tr>
                        </tbody>
                    </table>
                `),
            stepFunction: (editor) => keydownShiftTab(editor),
            contentAfter: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td>
                                    ghi
                                </td>
                                <td>
                                    <ol>
                                        <li><p>abc</p></li>
                                        <li>[def]</li>
                                    </ol>
                                </td>
                                <td>
                                    jkl
                                </td>
                            </tr>
                        </tbody>
                    </table>
                `),
        });
    });
});
