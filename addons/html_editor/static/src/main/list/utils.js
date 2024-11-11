import { nextLeaf, previousLeaf } from "@html_editor/utils/dom_info";
import { fontSizeItems } from "../font/font_plugin";

export function createList(document, mode) {
    const node = document.createElement(mode === "OL" ? "OL" : "UL");
    if (mode === "CL") {
        node.classList.add("o_checklist");
    }
    return node;
}

// @todo @phoenix Change this API (and implementation), as all use cases seem to
// create a list with a single LI
export function insertListAfter(document, afterNode, mode, content = []) {
    const list = createList(document, mode);
    afterNode.after(list);
    let fontSize;
    list.append(
        ...content.map((c) => {
            const li = document.createElement("LI");
            li.append(...[].concat(c));
            const font = li.querySelector("font");
            if (font && !previousLeaf(font, list) && !nextLeaf(font, list)) {
                li.style.setProperty("--marker-color", font.style.color);
            }
            const span = li.querySelector("span");
            if (span && !previousLeaf(span, list) && !nextLeaf(span, list)) {
                const variableName = fontSizeItems.find((el) =>
                    span.classList.contains(el.className)
                ).variableName;
                if (variableName) {
                    const doc = document.documentElement;
                    fontSize = getComputedStyle(doc).getPropertyValue(`--${variableName}`);
                } else if (span.style.fontSize) {
                    fontSize = span.style.fontSize;
                }
            }
            return li;
        })
    );
    if (fontSize) {
        list.style.setProperty("--marker-size", fontSize);
        list.style.listStylePosition = "inside";
    }
    return list;
}

/* Returns true if the two lists are of the same type among:
 * - OL
 * - regular UL
 * - checklist (ul.o_checklist)
 * - container for nested lists (li.oe-nested)
 */
export function compareListTypes(a, b) {
    if (a.tagName !== b.tagName) {
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
