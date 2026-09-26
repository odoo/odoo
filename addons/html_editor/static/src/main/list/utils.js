import { getTextColorOrClass } from "@html_editor/utils/color";
import { unwrapContents, removeClass, removeStyle } from "@html_editor/utils/dom";
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
        const moveFormattingToListItem = (element, property, format) => {
            if (!format) {
                return;
            }
            if (format.type === "class") {
                li.classList.add(format.value);
                removeClass(element, format.value);
            } else {
                li.style.setProperty(property, format.value);
                removeStyle(element, property);
            }
        };

        let current = li;
        while (current.childNodes.length === 1) {
            const child = current.firstElementChild;
            if (!child) {
                break;
            }
            const tag = child.tagName;
            if (tag === "FONT" || tag === "SPAN") {
                moveFormattingToListItem(child, "color", getTextColorOrClass(child));
                if (tag === "SPAN") {
                    moveFormattingToListItem(child, "font-size", getFontSizeOrClass(child));
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
