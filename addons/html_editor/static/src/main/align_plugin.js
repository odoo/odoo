import { Plugin } from "@html_editor/plugin";
import { closestBlock } from "@html_editor/utils/blocks";
import { isVisibleTextNode } from "@html_editor/utils/dom_info";

export class AlignPlugin extends Plugin {
    static id = "align";
    static dependencies = ["selection"];
    resources = {
        user_commands: [
            { id: "alignLeft", run: () => this.align("left") },
            { id: "alignRight", run: () => this.align("right") },
            { id: "alignCenter", run: () => this.align("center") },
            { id: "justify", run: () => this.align("justify") },
        ],
    };

    align(mode) {
        const visitedBlocks = new Set();
        const targetedNodes = this.dependencies.selection.getTargetedNodes();
        for (const node of targetedNodes) {
            if (isVisibleTextNode(node)) {
                const block = closestBlock(node);
                if (!visitedBlocks.has(block)) {
                    // todo @phoenix: check if it s correct in right to left ?
                    let textAlign = getComputedStyle(block).textAlign;
                    textAlign = textAlign === "start" ? "left" : textAlign;
                    if (textAlign !== mode && block.isContentEditable) {
                        block.style.textAlign = mode;
                    }
                    visitedBlocks.add(block);
                }
            }
        }
    }
}
