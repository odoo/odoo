import { Plugin } from "@html_editor/plugin";

/**
 * In the text composer, a new line is a line break (`<br>`) in the current
 * block, like in a textarea, rather than a new paragraph. This applies to Enter
 * when it does not send the message (e.g. on mobile) and to pasted multi-line
 * text.
 */
export class TextLineBreakPlugin extends Plugin {
    static id = "textLineBreak";
    static dependencies = ["lineBreak"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        split_element_block_overrides: ({ targetNode, targetOffset }) => {
            this.dependencies.lineBreak.insertLineBreakElement({ targetNode, targetOffset });
            return true;
        },
    };
}
