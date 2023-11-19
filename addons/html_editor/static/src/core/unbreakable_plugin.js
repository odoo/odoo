import { Plugin } from "../plugin";
import { closestBlock } from "../utils/blocks";
import { isUnbreakable } from "../utils/dom_info";

export class UnbreakablePlugin extends Plugin {
    static name = "unbreakable";
    static dependencies = ["line_break"];
    /** @type { (p: UnbreakablePlugin) => Record<string, any> } */
    static resources = (p) => ({
        split_element_block: [{ callback: p.handleSplitUnbreakable.bind(p) }],
    });

    handleSplitUnbreakable({ targetNode, targetOffset }) {
        const firstBlock = closestBlock(targetNode);
        if (isUnbreakable(firstBlock)) {
            this.shared.insertLineBreakElement({ targetNode, targetOffset });
            return true;
        }
    }
}
