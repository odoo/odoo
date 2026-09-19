import { getTextColorOrClass } from "@html_editor/utils/color";
import { unwrapContents } from "@html_editor/utils/dom";
import { getFontSizeOrClass } from "@html_editor/utils/formatting";

export function createList(document, mode) {
    const node = document.createElement(mode === "OL" ? "OL" : "UL");
    if (mode === "CL") {
        node.classList.add("o_checklist");
    }
    return node;
}

export function insertListAfter(document, afterNode, mode, content = []) {
    const parent = afterNode.parentNode;
    const nextSibling = afterNode.nextSibling;
    const list = createList(document, mode);
    const li = document.createElement("LI");
    li.append(...content);
    if (content.length === 1 && content[0].nodeType === Node.ELEMENT_NODE) {
        const moveFormatting = (element, property, info) => {
            if (!info) {
                return;
            }
            if (info.type === "class") {
                li.classList.add(info.value);
                element.classList.remove(info.value);
            } else {
                li.style.setProperty(property, info.value);
                element.style.removeProperty(property);
            }
        };

        let current = li;
        while (current.childNodes.length === 1) {
            const child = current.firstChild;
            if (child.nodeType !== Node.ELEMENT_NODE) {
                break;
            }
            const tag = child.tagName;
            if (tag === "FONT" || tag === "SPAN") {
                moveFormatting(child, "color", getTextColorOrClass(child));
                if (tag === "SPAN") {
                    moveFormatting(child, "font-size", getFontSizeOrClass(child));
                }
                if (!child.style.length && !child.classList.length) {
                    unwrapContents(child);
                    continue;
                }
            }
            current = child;
        }
    }
    list.append(li);
    parent.insertBefore(list, nextSibling);
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
