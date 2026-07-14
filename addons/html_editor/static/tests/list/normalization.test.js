import { describe, test } from "@odoo/hoot";
import { testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";

describe("Inlines and blocks in list item", () => {
    test("should allow paragraphs in list item", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>
                        <p>abc</p>
                    </li>
                </ul>
            `),
            contentAfter: unformat(`
                  <ul>
                    <li>
                        <p>abc</p>
                    </li>
                </ul>
            `),
        });
    });
    test("should allow inlines in list item, when there are no blocks", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>
                        abc<strong>def</strong>
                    </li>
                </ul>
            `),
            contentAfter: unformat(`
                  <ul>
                    <li>
                        abc<strong>def</strong>
                    </li>
                </ul>
            `),
        });
    });
    test("should wrap inlines in Ps when there are blocks in the list item", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>
                        abc
                        <p>paragraph</p>
                        <strong>def</strong>
                    </li>
                </ul>
            `),
            contentAfter: unformat(`
                  <ul>
                    <li>
                        <p>abc</p>
                        <p>paragraph</p>
                        <p><strong>def</strong></p>
                    </li>
                </ul>
            `),
        });
    });

    test("should wrap inlines in Ps when there are blocks in the list item (2)", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>
                        abc<br>def
                        <h1>ghi</h1>
                    </li>
                </ul>
            `),
            contentAfter: unformat(`
                  <ul>
                    <li>
                        <p>abc</p>
                        <p>def</p>
                        <h1>ghi</h1>
                    </li>
                </ul>
            `),
        });
    });

    test("should wrap inlines in paragraph preserving selection", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>
                        <h1>abc</h1>
                        abc[<i>def</i>]
                    </li>
                </ul>
            `),
            contentAfter: unformat(`
                <ul>
                    <li>
                        <h1>abc</h1>
                        <p>abc[<i>def</i></p>]
                    </li>
                </ul>
            `),
        });
    });
    test("should wrap inlines in paragraph preserving selection (2)", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>
                        abc<i>def</i>
                        [<h1>abc</h1>]
                    </li>
                </ul>
            `),
            contentAfter: unformat(`
                <ul>
                    <li>
                        <p>abc<i>def</i></p>
                        [<h1>abc</h1>]
                    </li>
                </ul>
            `),
        });
    });
});

describe("Nested lists without class oe-nested", () => {
    test("should normalize nested lists without class oe-nested", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>abc</li>
                    <li>def</li>
                    <ul>
                        <li>ghi</li>
                        <li>jkl</li>
                    </ul>
                    <ol>
                        <li>mno</li>
                        <li>pqr</li>
                    </ol>
                </ul>
            `),
            contentAfter: unformat(`
                <ul>
                    <li>abc</li>
                    <li>def</li>
                    <li class="oe-nested">
                        <ul>
                            <li>ghi</li>
                            <li>jkl</li>
                        </ul>
                    </li>
                    <li class="oe-nested">
                        <ol>
                            <li>mno</li>
                            <li>pqr</li>
                        </ol>
                    </li>
                </ul>
            `),
        });
    });
});
