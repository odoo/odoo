import { isBlock } from "./blocks";
import { isPhrasingContent } from "../utils/dom_info";

// @todo @phoenix: consider using the wrapInlinesInBlocks utils instead.

export function initElementForEdition(element, options = {}) {
    const document = element.ownerDocument;
    // Detect if the editable base element contain orphan inline nodes. If
    // so we transform the base element HTML to put those orphans inside
    // `<p>` containers.
    const orphanInlineChildNodes = [...element.childNodes].find(
        (n) => !isBlock(n) && (n.nodeType === Node.ELEMENT_NODE || n.textContent.trim() !== "")
    );
    if (orphanInlineChildNodes && !options.allowInlineAtRoot) {
        const childNodes = [...element.childNodes];
        const blockMap = new WeakMap();
        for (const node of childNodes) {
            blockMap.set(node, isBlock(node));
        }
        const newChildren = [];
        let currentBlock = document.createElement("DIV");
        let hasOnlyPhrasingContent = true;
        currentBlock.style.marginBottom = "0";
        for (let i = 0; i < childNodes.length; i++) {
            const node = childNodes[i];
            const nodeIsBlock = blockMap.get(node);
            const nodeIsBR = node.nodeName === "BR";
            // Append to the P unless child is block or an unneeded BR.
            if (!(nodeIsBlock || (nodeIsBR && currentBlock.hasChildNodes()))) {
                currentBlock.append(node);
                if (!isPhrasingContent(node)) {
                    hasOnlyPhrasingContent = false;
                }
            }
            // Break paragraphs on blocks and BR.
            if (nodeIsBlock || nodeIsBR || childNodes.length === i + 1) {
                if (hasOnlyPhrasingContent) {
                    const block = document.createElement("P");
                    block.style.marginBottom = "0";
                    block.replaceChildren(...currentBlock.childNodes);
                    currentBlock = block;
                }
                // Ensure we don't add an empty P or a P containing only
                // formating spaces that should not be visible.
                if (currentBlock.hasChildNodes() && currentBlock.innerHTML.trim() !== "") {
                    newChildren.push(currentBlock);
                }
                currentBlock = document.createElement("DIV");
                currentBlock.style.marginBottom = "0";
                hasOnlyPhrasingContent = true;
                // Append block children directly to the template.
                if (nodeIsBlock) {
                    newChildren.push(node);
                }
            }
        }
        element.replaceChildren(...newChildren);
    }
}
