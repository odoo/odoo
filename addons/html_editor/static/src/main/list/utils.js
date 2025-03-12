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
    let fontSizeStyle;
    if (content.length === 1 && content[0].tagName === "FONT" && content[0].style.color) {
        li.style.color = content[0].style.color;
        li.append(...content[0].childNodes);
    } else if (
        content.length === 1 &&
        content[0].tagName === "SPAN" &&
        (fontSizeStyle = getFontSizeOrClass(content[0]))
    ) {
        if (fontSizeStyle.type === "font-size") {
            li.style.fontSize = fontSizeStyle.value;
        } else if (fontSizeStyle.type === "class") {
            li.classList.add(fontSizeStyle.value);
        }
        li.append(...content[0].childNodes);
    } else {
        li.append(...content);
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
