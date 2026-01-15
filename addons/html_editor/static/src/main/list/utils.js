import { unwrapContents } from "@html_editor/utils/dom";
import { closestElement, firstLeaf, lastLeaf } from "@html_editor/utils/dom_traversal";
import { getFontSizeOrClass } from "@html_editor/utils/formatting";

export function createList(document, mode) {
    const node = document.createElement(mode === "OL" ? "OL" : "UL");
    if (mode === "CL") {
        node.classList.add("o_checklist");
    }
    return node;
}

export function insertListAfter(document, afterNode, mode, content = []) {
    const list = createList(document, mode);
    afterNode.after(list);
    const li = document.createElement("LI");
    li.append(...content);
    if (content.length === 1 && content[0].nodeType === Node.ELEMENT_NODE) {
        const firstLeafNode = firstLeaf(content[0]);
        const lastLeafNode = lastLeaf(content[0]);
        const firstClosestFont = closestElement(firstLeafNode, "font");
        const lastClosestFont = closestElement(lastLeafNode, "font");
        if (firstClosestFont && lastClosestFont && firstClosestFont === lastClosestFont) {
            li.style.color = firstClosestFont.style.color;
            unwrapContents(firstClosestFont);
        }
        const firstClosestSpan = closestElement(firstLeafNode, "span");
        const lastClosestSpan = closestElement(lastLeafNode, "span");
        let fontSizeStyle;
        if (
            firstClosestSpan &&
            lastClosestSpan &&
            firstClosestSpan === lastClosestSpan &&
            (fontSizeStyle = getFontSizeOrClass(firstClosestSpan))
        ) {
            if (fontSizeStyle.type === "font-size") {
                li.style.fontSize = fontSizeStyle.value;
            } else if (fontSizeStyle.type === "class") {
                li.classList.add(fontSizeStyle.value);
            }
            unwrapContents(firstClosestSpan);
        }
    }
    list.append(li);
    return list;
}

/* Returns true if the two lists are of the same type among:
 * - OL
 * - regular UL
 * - checklist (ul.o_checklist)
 * - container for nested lists (li.oe-nested)
 */
export function compareListTypes(a, b) {
    if (!a || !b || a.tagName !== b.tagName) {
        return false;
    }
    if (a.classList.contains("o_checklist") !== b.classList.contains("o_checklist")) {
        return false;
    }
    if (a.tagName === "LI") {
        if (a.classList.contains("oe-nested") !== b.classList.contains("oe-nested")) {
            return false;
        }
        return compareListTypes(a.firstElementChild, b.firstElementChild);
    }
    return true;
}

export function isListItem(node) {
    return node.nodeName === "LI" && !node.classList.contains("nav-item");
}
