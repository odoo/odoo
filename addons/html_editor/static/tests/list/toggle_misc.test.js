import { animationFrame, click, describe, expect, hover, test, waitFor } from "@odoo/hoot";
import { setupEditor, testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { toggleOrderedList, toggleUnorderedList, toggleCheckList } from "../_helpers/user_actions";
import { expandToolbar } from "../_helpers/toolbar";
import { getContent } from "../_helpers/selection";
import { press, queryOne } from "@odoo/hoot-dom";

async function setupListDropdown(content) {
    const { el } = await setupEditor(content);

    await expandToolbar();
    await waitFor(".btn[name='list_selector']");
    await click(".btn[name='list_selector']");
    await waitFor(".o-we-toolbar-dropdown button[name='bulleted_list']");

    return { el };
}

function getListItem(name) {
    return queryOne(`.o-we-toolbar-dropdown button[name='${name}']`);
}

describe("Mixed", () => {
    test("should turn an ordered list into an unordered list (1)", async () => {
        await testEditor({
            contentBefore: "<ol><li>a[b]c</li></ol>",
            stepFunction: toggleUnorderedList,
            contentAfter: "<ul><li>a[b]c</li></ul>",
        });
    });

    test("should turn an ordered list into an unordered list (2)", async () => {
        await testEditor({
            contentBefore: '<ol><li><a href="http://test.com">[test]</a></li></ol>',
            stepFunction: toggleUnorderedList,
            contentAfter: '<ul><li><a href="http://test.com">[test]</a></li></ul>',
        });
    });

    test("should turn an unordered list into an ordered list (1)", async () => {
        await testEditor({
            contentBefore: "<ul><li>a[b]c</li></ul>",
            stepFunction: toggleOrderedList,
            contentAfter: "<ol><li>a[b]c</li></ol>",
        });
    });

    test("should turn an unordered list into an ordered list (2)", async () => {
        await testEditor({
            contentBefore: '<ul><li><a href="http://test.com">[test]</a></li></ul>',
            stepFunction: toggleOrderedList,
            contentAfter: '<ol><li><a href="http://test.com">[test]</a></li></ol>',
        });
    });

    test("should turn a paragraph and an unordered list item into an ordered list and an unordered list", async () => {
        await testEditor({
            contentBefore: "<p>a[b</p><ul><li>c]d</li><li>ef</li></ul>",
            stepFunction: toggleOrderedList,
            contentAfter: "<ol><li>a[b</li><li>c]d</li><li>ef</li></ol>",
        });
    });

    test("should turn a p, an ul list with among others one nested ul, and another p into one ol with a nested ol", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <p>a[b</p>
                    <ul>
                        <li><p>cd</p>
                            <ul>
                                <li>ef</li>
                            </ul>
                        </li>
                        <li>gh</li>
                    </ul>
                    <p>i]j</p>`),
            stepFunction: toggleOrderedList,
            contentAfter: unformat(`
                    <ol>
                        <li>a[b</li>
                        <li><p>cd</p>
                            <ol>
                                <li>ef</li>
                            </ol>
                        </li>
                        <li>gh</li>
                        <li>i]j</li>
                    </ol>`),
        });
    });

    test("should turn unordered list into ordered list with block style applied to it", async () => {
        await testEditor({
            contentBefore: unformat(`
                                <ul>
                                    <li><h1>abc</h1>
                                        <ul>
                                            <li><h2>a[bc</h2>
                                                <ul>
                                                    <li><h2>abc</h2></li>
                                                    <li><h3>abc</h3></li>
                                                    <li><h4>abc</h4></li>
                                                </ul>
                                            </li>
                                            <li><h2>abc</h2></li>
                                        </ul>
                                    </li>
                                    <li><h1>abc</h1>
                                        <ul>
                                            <li><h2>abc</h2>
                                                <ul>
                                                    <li><h2>abc</h2></li>
                                                    <li><h3>abc</h3></li>
                                                    <li><h4>abc</h4></li>
                                                </ul>
                                            </li>
                                            <li><h2>a]bc</h2></li>
                                        </ul>
                                    </li>
                                    <li><h1>abc</h1></li>
                                </ul>
                            `),
            stepFunction: toggleOrderedList,
            contentAfter: unformat(`
                                <ol>
                                    <li><h1>abc</h1>
                                        <ol>
                                            <li><h2>a[bc</h2>
                                                <ol>
                                                    <li><h2>abc</h2></li>
                                                    <li><h3>abc</h3></li>
                                                    <li><h4>abc</h4></li>
                                                </ol>
                                            </li>
                                            <li><h2>abc</h2></li>
                                        </ol>
                                    </li>
                                    <li><h1>abc</h1>
                                        <ol>
                                            <li><h2>abc</h2>
                                                <ol>
                                                    <li><h2>abc</h2></li>
                                                    <li><h3>abc</h3></li>
                                                    <li><h4>abc</h4></li>
                                                </ol>
                                            </li>
                                            <li><h2>a]bc</h2></li>
                                        </ol>
                                    </li>
                                    <li><h1>abc</h1></li>
                                </ol>`),
        });
    });

    test("should turn unordered list into ordered list with block and inline style applied to it", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul>
                        <li><h1><strong>abc</strong></h1>
                            <ul>
                                <li><h3><strong>a[bc</strong></h3>
                                    <ul>
                                        <li><h2><em>abc</em></h2></li>
                                        <li><h2><s>abc</s></h2></li>
                                        <li><h2><u>abc</u></h2></li>
                                    </ul>
                                </li>
                                <li><h1><strong>abc</strong></h1></li>
                            </ul>
                        </li>
                        <li><h1><strong>abc</strong></h1>
                            <ul>
                                <li><h3><strong>abc</strong></h3>
                                    <ul>
                                        <li><h2><em>abc</em></h2></li>
                                        <li><h2><s>abc</s></h2></li>
                                        <li><h2><u>abc</u></h2></li>
                                    </ul>
                                </li>
                                <li><h1><strong>a]bc</strong></h1></li>
                            </ul>
                        </li>
                        <li><h1><strong>abc</strong></h1></li>
                    </ul>
                    `),
            stepFunction: toggleOrderedList,
            contentAfter: unformat(`
                    <ol>
                        <li><h1><strong>abc</strong></h1>
                            <ol>
                                <li><h3><strong>a[bc</strong></h3>
                                    <ol>
                                        <li><h2><em>abc</em></h2></li>
                                        <li><h2><s>abc</s></h2></li>
                                        <li><h2><u>abc</u></h2></li>
                                    </ol>
                                </li>
                                <li><h1><strong>abc</strong></h1></li>
                            </ol>
                        </li>
                        <li><h1><strong>abc</strong></h1>
                            <ol>
                                <li><h3><strong>abc</strong></h3>
                                    <ol>
                                        <li><h2><em>abc</em></h2></li>
                                        <li><h2><s>abc</s></h2></li>
                                        <li><h2><u>abc</u></h2></li>
                                    </ol>
                                </li>
                                <li><h1><strong>a]bc</strong></h1></li>
                            </ol>
                        </li>
                        <li><h1><strong>abc</strong></h1></li>
                    </ol>`),
        });
    });

    test("should turn an unordered list item and a paragraph into two list items within an ordered list", async () => {
        await testEditor({
            contentBefore: "<ul><li>ab</li><li>c[d</li></ul><p>e]f</p>",
            stepFunction: toggleOrderedList,
            contentAfter: "<ol><li>ab</li><li>c[d</li><li>e]f</li></ol>",
        });
    });

    test("should turn an unordered list, a paragraph and an ordered list into one ordered list with three list items", async () => {
        await testEditor({
            contentBefore: "<ul><li>a[b</li></ul><p>cd</p><ol><li>e]f</li></ol>",
            stepFunction: toggleOrderedList,
            contentAfter: "<ol><li>a[b</li><li>cd</li><li>e]f</li></ol>",
        });
    });

    test("should turn an unordered list item, a paragraph and an ordered list into one ordered list with all three as list items", async () => {
        await testEditor({
            contentBefore: "<ul><li>ab</li><li>c[d</li></ul><p>ef</p><ol><li>g]h</li></ol>",
            stepFunction: toggleOrderedList,
            contentAfter: "<ol><li>ab</li><li>c[d</li><li>ef</li><li>g]h</li></ol>",
        });
    });

    test("should turn an ordered list, a paragraph and an unordered list item into one ordered list with all three as list items", async () => {
        await testEditor({
            contentBefore: "<ol><li>a[b</li></ol><p>cd</p><ul><li>e]f</li><li>gh</li></ul>",
            stepFunction: toggleOrderedList,
            contentAfter: "<ol><li>a[b</li><li>cd</li><li>e]f</li><li>gh</li></ol>",
        });
    });

    test("should turn an unordered list within an unordered list into an ordered list within an unordered list", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul>
                        <li><p>ab</p>
                            <ul>
                                <li>c[d</li>
                                <li>e]f</li>
                            </ul>
                        </li>
                        <li>gh</li>
                    </ul>`),
            stepFunction: toggleOrderedList,
            contentAfter: unformat(`
                    <ul>
                        <li><p>ab</p>
                            <ol>
                                <li>c[d</li>
                                <li>e]f</li>
                            </ol>
                        </li>
                        <li>gh</li>
                    </ul>`),
        });
    });

    test("should turn an unordered list with mixed nested elements into an ordered list with only unordered elements", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul>
                        <li>a[b</li>
                        <li><p>cd</p>
                            <ul>
                                <li>ef</li>
                                <li><p>gh</p>
                                    <ol>
                                        <li>ij</li>
                                        <li><p>kl</p>
                                            <ul>
                                                <li>mn</li>
                                            </ul>
                                        </li>
                                        <li>op</li>
                                    </ol>
                                </li>
                            </ul>
                        </li>
                        <li>q]r</li>
                        <li>st</li>
                    </ul>`),
            stepFunction: toggleOrderedList,
            contentAfter: unformat(`
                    <ol>
                        <li>a[b</li>
                        <li><p>cd</p>
                            <ol>
                                <li>ef</li>
                                <li><p>gh</p>
                                    <ol>
                                        <li>ij</li>
                                        <li><p>kl</p>
                                            <ol>
                                                <li>mn</li>
                                            </ol>
                                        </li>
                                        <li>op</li>
                                    </ol>
                                </li>
                            </ol>
                        </li>
                        <li>q]r</li>
                        <li>st</li>
                    </ol>`),
        });
    });

    test("should convert within mixed lists", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul>
                        <li>a</li>
                        <li><p>b</p>
                            <ol>
                                <li>c</li>
                                <li><p>d</p>
                                    <ul>
                                        <li>[]e</li>
                                        <li><p>f</p>
                                            <ul>
                                                <li>g</li>
                                            </ul>
                                        </li>
                                        <li>h</li>
                                    </ul>
                                </li>
                            </ol>
                        </li>
                        <li>qr</li>
                        <li>st</li>
                    </ul>`),
            stepFunction: toggleOrderedList,
            contentAfter: unformat(`
                    <ul>
                        <li>a</li>
                        <li><p>b</p>
                            <ol>
                                <li>c</li>
                                <li><p>d</p>
                                    <ol>
                                        <li>[]e</li>
                                        <li><p>f</p>
                                            <ul>
                                                <li>g</li>
                                            </ul>
                                        </li>
                                        <li>h</li>
                                    </ol>
                                </li>
                            </ol>
                        </li>
                        <li>qr</li>
                        <li>st</li>
                    </ul>`),
        });
    });

    test("should turn an unordered list into a checklist (1)", async () => {
        await testEditor({
            contentBefore: "<ul><li>a[b]c</li></ul>",
            stepFunction: toggleCheckList,
            contentAfter: '<ul class="o_checklist"><li>a[b]c</li></ul>',
        });
    });

    test("should turn an unordered list into a checklist (2)", async () => {
        await testEditor({
            contentBefore: '<ul><li><a href="http://test.com">[test]</a></li></ul>',
            stepFunction: toggleCheckList,
            contentAfter:
                '<ul class="o_checklist"><li><a href="http://test.com">[test]</a></li></ul>',
        });
    });

    test("should turn an unordered list into a checklist just after a checklist", async () => {
        await testEditor({
            contentBefore:
                '<ul class="o_checklist"><li class="o_checked">abc</li></ul><ul><li>d[e]f</li></ul>',
            stepFunction: toggleCheckList,
            contentAfter:
                '<ul class="o_checklist"><li class="o_checked">abc</li><li>d[e]f</li></ul>',
        });
    });

    test("should turn an unordered list into a checklist just after a checklist and inside a checklist", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li><p>title</p>
                            <ul class="o_checklist">
                                <li class="o_checked">abc</li>
                            </ul>
                            <ul>
                                <li>d[e]f</li>
                            </ul>
                        </li>
                    </ul>`),
            stepFunction: toggleCheckList,
            contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li><p>title</p>
                            <ul class="o_checklist">
                                <li class="o_checked">abc</li>
                                <li>d[e]f</li>
                            </ul>
                        </li>
                    </ul>`),
        });
    });
});

describe("availability", () => {
    test("list tool should be available from span inside editable block", async () => {
        await setupEditor(
            `<div contenteditable="true"><p><span contenteditable="true">ab[cde]fg</span></p></div>`
        );
        await expandToolbar();
        expect(".btn[name='list_selector']").toHaveCount(1);
    });
    test("list tool should not be available from editable span inside non-editable block", async () => {
        await setupEditor(
            `<div contenteditable="false"><p><span contenteditable="true">ab[cde]fg</span></p></div>`
        );
        await expandToolbar();
        expect(".btn[name='list_selector']").toHaveCount(0);
    });
    test("list tool should not be available from editable p inside non-editable block", async () => {
        await setupEditor(
            `<div contenteditable="false"><p contenteditable="true">ab[cde]fg</p></div>`
        );
        await expandToolbar();
        expect(".btn[name='list_selector']").toHaveCount(0);
    });

    test("list tool should be available from editable p inside editable list", async () => {
        await setupEditor(
            `<ul contenteditable="true"><li><p contenteditable="true">ab[cde]fg</p></li></ul>`
        );
        await expandToolbar();
        expect(".btn[name='list_selector']").toHaveCount(1);
    });
    test("list tool should not be available from editable p inside non-editable list", async () => {
        await setupEditor(
            `<ul contenteditable="false"><li><p contenteditable="true">ab[cde]fg</p></li></ul>`
        );
        await expandToolbar();
        expect(".btn[name='list_selector']").toHaveCount(0);
    });
});

describe("List type preview with mouse hover", () => {
    test.tags("desktop");
    test("should preview different list types on hover when no list is applied", async () => {
        const { el } = await setupListDropdown("<p>a[bc]d</p>");

        await hover(getListItem("bulleted_list"));
        await animationFrame();
        expect(getContent(el)).toBe(`<ul><li>a[bc]d</li></ul>`);

        await hover(getListItem("numbered_list"));
        await animationFrame();
        expect(getContent(el)).toBe(`<ol><li>a[bc]d</li></ol>`);

        await hover(getListItem("checklist"));
        await animationFrame();
        expect(getContent(el)).toBe(`<ul class="o_checklist"><li>a[bc]d</li></ul>`);
    });

    test.tags("desktop");
    test("should preview different list types on hover when a list is already applied", async () => {
        const { el } = await setupListDropdown("<ol><li>a[bc]d</li></ol>");

        await hover(getListItem("bulleted_list"));
        await animationFrame();
        expect(getContent(el)).toBe(`<ul><li>a[bc]d</li></ul>`);

        await hover(getListItem("numbered_list"));
        await animationFrame();
        expect(getContent(el)).toBe(`<p>a[bc]d</p>`);

        await hover(getListItem("checklist"));
        await animationFrame();
        expect(getContent(el)).toBe(`<ul class="o_checklist"><li>a[bc]d</li></ul>`);
    });

    test.tags("desktop");
    test("should revert preview when mouse leaves without applying list type", async () => {
        const { el } = await setupListDropdown("<p>a[bc]d</p>");

        await hover(getListItem("bulleted_list"));
        await animationFrame();
        expect(getContent(el)).toBe(`<ul><li>a[bc]d</li></ul>`);

        await hover(el);

        expect(getContent(el)).toBe(`<p>a[bc]d</p>`);
    });
});

describe("List type preview with keyboard", () => {
    test.tags("desktop");
    test("should preview different list types while navigating with keyboard", async () => {
        const { el } = await setupListDropdown("<p>a[bc]d</p>");

        await press("ArrowDown");
        await animationFrame();
        expect(getListItem("bulleted_list")).toBeFocused();
        expect(getContent(el)).toBe(`<ul><li>a[bc]d</li></ul>`);

        await press("ArrowDown");
        await animationFrame();
        expect(getListItem("numbered_list")).toBeFocused();
        expect(getContent(el)).toBe(`<ol><li>a[bc]d</li></ol>`);

        await press("ArrowDown");
        await animationFrame();
        expect(getListItem("checklist")).toBeFocused();
        expect(getContent(el)).toBe(`<ul class="o_checklist"><li>a[bc]d</li></ul>`);
    });

    test.tags("desktop");
    test("should revert preview when Escape closes the dropdown (no initial list)", async () => {
        const { el } = await setupListDropdown("<p>a[bc]d</p>");

        await press("ArrowDown");
        await animationFrame();
        expect(getListItem("bulleted_list")).toBeFocused();
        expect(getContent(el)).toBe(`<ul><li>a[bc]d</li></ul>`);

        await press("Escape");
        await animationFrame();

        expect(getContent(el)).toBe(`<p>a[bc]d</p>`);
    });

    test.tags("desktop");
    test("should revert preview when Escape closes the dropdown (existing list)", async () => {
        const { el } = await setupListDropdown("<ul><li>a[bc]d</li></ul>");

        await press("ArrowDown");
        await animationFrame();
        expect(getListItem("bulleted_list")).toBeFocused();
        expect(getContent(el)).toBe(`<p>a[bc]d</p>`);

        await press("Escape");
        await animationFrame();

        expect(getContent(el)).toBe(`<ul><li>a[bc]d</li></ul>`);
    });
});

describe("List type preview with mixed interactions", () => {
    test.tags("desktop");
    test("should update preview when switching from hover to keyboard navigation", async () => {
        const { el } = await setupListDropdown("<p>a[bc]d</p>");

        await hover(getListItem("bulleted_list"));
        await animationFrame();
        expect(getContent(el)).toBe(`<ul><li>a[bc]d</li></ul>`);

        await press("ArrowDown");
        await animationFrame();

        expect(getListItem("numbered_list")).toBeFocused();
        expect(getContent(el)).toBe(`<ol><li>a[bc]d</li></ol>`);
    });

    test.tags("desktop");
    test("should revert preview when pressing Escape after switching from hover to keyboard navigation", async () => {
        const { el } = await setupListDropdown("<ol><li>a[bc]d</li></ol>");

        await hover(getListItem("checklist"));
        await animationFrame();
        expect(getContent(el)).toBe(`<ul class="o_checklist"><li>a[bc]d</li></ul>`);

        await press("ArrowDown");
        await animationFrame();

        expect(getListItem("bulleted_list")).toBeFocused();
        expect(getContent(el)).toBe(`<ul><li>a[bc]d</li></ul>`);

        await press("Escape");
        await animationFrame();

        expect(getContent(el)).toBe(`<ol><li>a[bc]d</li></ol>`);
    });
});
