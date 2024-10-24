import { Plugin } from "@html_editor/plugin";
import { closestBlock } from "@html_editor/utils/blocks";
import { isVisibleTextNode } from "@html_editor/utils/dom_info";

export class JustifyPlugin extends Plugin {
    static name = "justify";
    static dependencies = ["selection"];
    resources = {
        user_commands: [
            { id: "justifyLeft", run: () => this.align("left") },
            { id: "justifyRight", run: () => this.align("right") },
            { id: "justifyCenter", run: () => this.align("center") },
            { id: "justifyFull", run: () => this.align("justify") },
        ],
    };

    align(mode) {
        const visitedBlocks = new Set();
        const traversedNode = this.shared.getTraversedNodes();
        for (const node of traversedNode) {
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
