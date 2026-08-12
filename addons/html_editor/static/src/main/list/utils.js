import { getTextColorOrClass } from "@html_editor/utils/color";
import { unwrapContents, removeClass, removeStyle } from "@html_editor/utils/dom";
import { getFontSizeOrClass } from "@html_editor/utils/formatting";
import { isColorGradient } from "@web/core/utils/colors";

const bulletFormats = {
    color: (element) =>
        isColorGradient(element.style.backgroundImage) ? null : getTextColorOrClass(element),
    "font-size": getFontSizeOrClass,
};

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
        let current = li;
        while (current.childNodes.length === 1 && current.children.length) {
            const child = current.firstElementChild;
            const tag = child.tagName;
            if (tag === "FONT" || tag === "SPAN") {
                for (const [property, getFormat] of Object.entries(bulletFormats)) {
                    const format = getFormat(child);
                    if (format?.type === "class") {
                        li.classList.add(format.value);
                        removeClass(child, format.value);
                    } else if (format) {
                        li.style.setProperty(property, format.value);
                        removeStyle(child, property);
                    }
                }
                if (!child.hasAttributes()) {
                    unwrapContents(child);
                    continue;
                }
            }
            current = child;
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
