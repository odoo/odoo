import { describe, test } from "@odoo/hoot";
import { testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { deleteBackward } from "../_helpers/user_actions";

describe("Adjust base container on delete", () => {
    test("should remove empty o-paragraph block", async () => {
        await testEditor({
            contentBefore: unformat(`
                <div>
                    <div class="o-paragraph">[]<br></div>
                </div>`),
            stepFunction: async (editor) => {
                deleteBackward(editor);
            },
            contentAfterEdit: unformat(`
                <div class="o-paragraph o-we-hint" placeholder='Type "/" for commands'>[]<br></div>
            `),
        });
    });

    test("should remove empty o-paragraph block after text", async () => {
        await testEditor({
            contentBefore: unformat(`
                <div>
                    abc<div class="o-paragraph">[]<br></div>
                </div>`),
            stepFunction: async (editor) => {
                deleteBackward(editor);
            },
            contentAfterEdit: unformat(`
                <div class="o-paragraph">abc[]</div>
            `),
        });
    });

    test("should remove div with selected text", async () => {
        await testEditor({
            contentBefore: unformat(`
                <div>
                    <div>[abc]</div>
                </div>`),
            stepFunction: async (editor) => {
                deleteBackward(editor);
            },
            contentAfterEdit: unformat(`
                <div class="o-paragraph o-we-hint" placeholder='Type "/" for commands'>[]<br></div>
            `),
        });
    });

    test("should remove empty nested paragraph", async () => {
        await testEditor({
            contentBefore: unformat(`
                <div>
                    <div>
                        <p>[]<br></p>
                    </div>
                </div>`),
            stepFunction: async (editor) => {
                deleteBackward(editor);
            },
            contentAfterEdit: unformat(`
                <div><div class="o-paragraph o-we-hint" placeholder='Type "/" for commands'>[]<br></div></div>
            `),
        });
    });

    test("should not remove standalone paragraph", async () => {
        await testEditor({
            contentBefore: unformat(`
                <p>[]<br></p>
            `),
            stepFunction: async (editor) => {
                deleteBackward(editor);
            },
            contentAfterEdit: unformat(`
                <p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>
            `),
        });
    });

    test("should not remove unremovable div with selected text", async () => {
        await testEditor({
            contentBefore: unformat(`
                 <div class="oe_unremovable">
                    [abc]
                </div>`),
            stepFunction: async (editor) => {
                deleteBackward(editor);
            },
            contentAfterEdit: unformat(`
                <div class="oe_unremovable">[]<br></div>
            `),
        });
    });

    test("should keep paragraph inside unremovable div", async () => {
        await testEditor({
            contentBefore: unformat(`
                <div class="oe_unremovable">
                    <p>[abc]</p>
                </div>`),
            stepFunction: async (editor) => {
                deleteBackward(editor);
            },
            contentAfterEdit: unformat(`
                <div class="oe_unremovable">
                    <p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>
                </div>
            `),
        });
    });

    test("should keep block inside non-editable parent", async () => {
        await testEditor({
            contentBefore: unformat(`
                <div contenteditable="false">
                    <div contenteditable="true">[abc]</div>
                </div>`),
            stepFunction: async (editor) => {
                deleteBackward(editor);
            },
            // The P is added by the deletion, not by `cleanEmptyStructuralContainers`.
            contentAfterEdit: unformat(`
                <div contenteditable="false">
                    <div contenteditable="true">
                        <p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>
                    </div>
                </div>
            `),
        });
    });

    test("should keep o-paragraph inside non-editable parent", async () => {
        await testEditor({
            contentBefore: unformat(`
                <div contenteditable="false">
                    <div contenteditable="true">
                        <div class="o-paragraph">[]<br></div>
                    </div>
                </div>`),
            stepFunction: async (editor) => {
                deleteBackward(editor);
            },
            contentAfterEdit: unformat(`
                <div contenteditable="false">
                    <div contenteditable="true">
                        <div class="o-paragraph o-we-hint" placeholder='Type "/" for commands'>[]<br></div>
                    </div>
                </div>
            `),
        });
    });

    test("should remove nested o-paragraph with inner paragraph", async () => {
        await testEditor({
            contentBefore: unformat(`
                <div>
                    <div class="o-paragraph">
                        <p class="inner-paragraph">[]<br></p>
                    </div>
                </div>`),
            stepFunction: async (editor) => {
                deleteBackward(editor);
            },
            contentAfterEdit: unformat(`
                <div>
                    <div class="o-paragraph o-we-hint" placeholder='Type "/" for commands'>[]</div>
                </div>
            `),
        });
    });

    test("should remove first of multiple consecutive empty blocks", async () => {
        await testEditor({
            contentBefore: unformat(`
                <div>
                    <div>[]<br></div>
                    <div><br></div>
                </div>`),
            stepFunction: async (editor) => {
                deleteBackward(editor);
            },
            contentAfterEdit: unformat(`
                <div>
                    <div class="o-paragraph o-we-hint" placeholder='Type "/" for commands'>[]<br></div>
                </div>
            `),
        });
    });

    test("should not remove block with cursor at beginning of content", async () => {
        await testEditor({
            contentBefore: unformat(`
                <div>
                    <div>[]text</div>
                </div>`),
            stepFunction: async (editor) => {
                deleteBackward(editor);
            },
            contentAfterEdit: unformat(`
                <div>
                    <div class="o-paragraph">[]text</div>
                </div>
            `),
        });
    });

    test("should merge blocks when range spans multiple o-paragraphs", async () => {
        await testEditor({
            contentBefore: unformat(`
                <div>
                    <div class="o-paragraph">[abc</div>
                    <div class="o-paragraph">def]</div>
                </div>`),
            stepFunction: async (editor) => {
                deleteBackward(editor);
            },
            contentAfterEdit: unformat(`
                <div class="o-paragraph o-we-hint" placeholder='Type "/" for commands'>[]<br></div>
            `),
        });
    });

    test("should remove o-paragraph inside nested non-editable structure", async () => {
        await testEditor({
            contentBefore: unformat(`
                <div contenteditable="false">
                    <div contenteditable="true">
                        <div class="o-paragraph">[]<br></div>
                    </div>
                </div>`),
            stepFunction: async (editor) => {
                deleteBackward(editor);
            },
            contentAfterEdit: unformat(`
                <div contenteditable="false">
                    <div contenteditable="true">
                        <div class="o-paragraph o-we-hint" placeholder='Type "/" for commands'>[]<br></div>
                    </div>
                </div>
            `),
        });
    });
});
