import { describe, test } from "@odoo/hoot";
import { testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";

describe("Paragraph in list item", () => {
    test("should unwrap paragraph preserving selection", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>
                        <h1>abc</h1>
                        <p>abc[<i>def</i>]</p>
                    </li>
                </ul>
            `),
            contentAfter: unformat(`
                <ul>
                    <li>
                        <h1>abc</h1>
                        abc[<i>def</i>]
                    </li>
                </ul>
            `),
        });
    });
    test("should unwrap paragraph preserving selection (2)", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>
                        <p>abc<i>def</i></p>
                        [<h1>abc</h1>]
                    </li>
                </ul>
            `),
            contentAfter: unformat(`
                <ul>
                    <li>
                        abc<i>def</i>
                        [<h1>abc</h1>]
                    </li>
                </ul>
            `),
        });
    });
});

// @todo @phoenix: write other tests about list normalization + preserve selection:
// - paragraph with class converted to span
// - empty paragraph gets removed
