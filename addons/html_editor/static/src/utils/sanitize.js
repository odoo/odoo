import { isBlock } from "./blocks";

// @todo @phoenix: consider using the wrapInlinesInParagraphs utils instead.

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
        let currentP = document.createElement("p");
        currentP.style.marginBottom = "0";
        for (let i = 0; i < childNodes.length; i++) {
            const node = childNodes[i];
            const nodeIsBlock = blockMap.get(node);
            const nodeIsBR = node.nodeName === "BR";
            // Append to the P unless child is block or an unneeded BR.
            if (!(nodeIsBlock || (nodeIsBR && currentP.childNodes.length))) {
                currentP.append(node);
            }
            // Break paragraphs on blocks and BR.
            if (nodeIsBlock || nodeIsBR || childNodes.length === i + 1) {
                // Ensure we don't add an empty P or a P containing only
                // formating spaces that should not be visible.
                if (currentP.childNodes.length && currentP.innerHTML.trim() !== "") {
                    newChildren.push(currentP);
                }
                currentP = currentP.cloneNode();
                // Append block children directly to the template.
                if (nodeIsBlock) {
                    newChildren.push(node);
                }
            }
        }
        element.replaceChildren(...newChildren);
    }
}
