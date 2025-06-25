import { describe, test } from "@odoo/hoot";
import { testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { toggleOrderedList, toggleUnorderedList, toggleCheckList } from "../_helpers/user_actions";

describe("Mixed", () => {
    test("should turn an ordered list into an unordered list", async () => {
        await testEditor({
            contentBefore: "<ol><li>a[b]c</li></ol>",
            stepFunction: toggleUnorderedList,
            contentAfter: "<ul><li>a[b]c</li></ul>",
        });
    });

    test("should turn an unordered list into an ordered list", async () => {
        await testEditor({
            contentBefore: "<ul><li>a[b]c</li></ul>",
            stepFunction: toggleOrderedList,
            contentAfter: "<ol><li>a[b]c</li></ol>",
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
                        <li>cd</li>
                        <li class="oe-nested">
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
                        <li>cd</li>
                        <li class="oe-nested">
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
                                    <li><h1>abc</h1></li>
                                    <li class="oe-nested">
                                        <ul>
                                            <li><h2>a[bc</h2></li>
                                            <li class="oe-nested">
                                                <ul>
                                                    <li><h2>abc</h2></li>
                                                    <li><h3>abc</h3></li>
                                                    <li><h4>abc</h4></li>
                                                </ul>
                                            </li>
                                            <li><h2>abc</h2></li>
                                        </ul>
                                    </li>
                                    <li><h1>abc</h1></li>
                                    <li class="oe-nested">
                                        <ul>
                                            <li><h2>abc</h2></li>
                                            <li class="oe-nested">
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
                                    <li><h1>abc</h1></li>
                                    <li class="oe-nested">
                                        <ol>
                                            <li><h2>a[bc</h2></li>
                                            <li class="oe-nested">
                                                <ol>
                                                    <li><h2>abc</h2></li>
                                                    <li><h3>abc</h3></li>
                                                    <li><h4>abc</h4></li>
                                                </ol>
                                            </li>
                                            <li><h2>abc</h2></li>
                                        </ol>
                                    </li>
                                    <li><h1>abc</h1></li>
                                    <li class="oe-nested">
                                        <ol>
                                            <li><h2>abc</h2></li>
                                            <li class="oe-nested">
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
                        <li><h1><strong>abc</strong></h1></li>
                        <li class="oe-nested">
                            <ul>
                                <li><h3><strong>a[bc</strong></h3></li>
                                <li class="oe-nested">
                                    <ul>
                                        <li><h2><em>abc</em></h2></li>
                                        <li><h2><s>abc</s></h2></li>
                                        <li><h2><u>abc</u></h2></li>
                                    </ul>
                                </li>
                                <li><h1><strong>abc</strong></h1></li>
                            </ul>
                        </li>
                        <li><h1><strong>abc</strong></h1></li>
                        <li class="oe-nested">
                            <ul>
                                <li><h3><strong>abc</strong></h3></li>
                                <li class="oe-nested">
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
                        <li><h1><strong>abc</strong></h1></li>
                        <li class="oe-nested">
                            <ol>
                                <li><h3><strong>a[bc</strong></h3></li>
                                <li class="oe-nested">
                                    <ol>
                                        <li><h2><em>abc</em></h2></li>
                                        <li><h2><s>abc</s></h2></li>
                                        <li><h2><u>abc</u></h2></li>
                                    </ol>
                                </li>
                                <li><h1><strong>abc</strong></h1></li>
                            </ol>
                        </li>
                        <li><h1><strong>abc</strong></h1></li>
                        <li class="oe-nested">
                            <ol>
                                <li><h3><strong>abc</strong></h3></li>
                                <li class="oe-nested">
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
                        <li>ab</li>
                        <li class="oe-nested">
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
                        <li>ab</li>
                        <li class="oe-nested">
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
                        <li>cd</li>
                        <li class="oe-nested">
                            <ul>
                                <li>ef</li>
                                <li>gh</li>
                                <li class="oe-nested">
                                    <ol>
                                        <li>ij</li>
                                        <li>kl</li>
                                        <li class="oe-nested">
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
                        <li>cd</li>
                        <li class="oe-nested">
                            <ol>
                                <li>ef</li>
                                <li>gh</li>
                                <li class="oe-nested">
                                    <ol>
                                        <li>ij</li>
                                        <li>kl</li>
                                        <li class="oe-nested">
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
                        <li>b</li>
                        <li class="oe-nested">
                            <ol>
                                <li>c</li>
                                <li>d</li>
                                <li class="oe-nested">
                                    <ul>
                                        <li>[]e</li>
                                        <li>f</li>
                                        <li class="oe-nested">
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
                        <li>b</li>
                        <li class="oe-nested">
                            <ol>
                                <li>c</li>
                                <li>d</li>
                                <li class="oe-nested">
                                    <ol>
                                        <li>[]e</li>
                                        <li>f</li>
                                        <li class="oe-nested">
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

    test("should turn an unordered list into a checklist", async () => {
        await testEditor({
            contentBefore: "<ul><li>a[b]c</li></ul>",
            stepFunction: toggleCheckList,
            contentAfter: '<ul class="o_checklist"><li>a[b]c</li></ul>',
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
                        <li class="o_checked">title</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">abc</li>
                            </ul>
                        </li>
                        <li class="oe-nested">
                            <ul>
                                <li>d[e]f</li>
                            </ul>
                        </li>
                    </ul>`),
            stepFunction: toggleCheckList,
            contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li class="o_checked">title</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">abc</li>
                                <li>d[e]f</li>
                            </ul>
                        </li>
                    </ul>`),
        });
    });
});
