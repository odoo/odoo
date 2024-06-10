export function getListMode(pnode) {
    if (pnode.tagName == "OL") {
        return "OL";
    }
    return pnode.classList.contains("o_checklist") ? "CL" : "UL";
}

export function createList(document, mode) {
    const node = document.createElement(mode == "OL" ? "OL" : "UL");
    if (mode == "CL") {
        node.classList.add("o_checklist");
    }
    return node;
}

// @todo @phoenix Change this API (and implementation), as all use cases seem to
// create a list with a single LI
export function insertListAfter(document, afterNode, mode, content = []) {
    const list = createList(document, mode);
    afterNode.after(list);
    list.append(
        ...content.map((c) => {
            const li = document.createElement("LI");
            li.append(...[].concat(c));
            return li;
        })
    );
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

export function applyToTree(root, func) {
    const modifiedRoot = func(root);
    let next = modifiedRoot.firstElementChild;
    while (next) {
        const modifiedNext = applyToTree(next, func);
        next = modifiedNext.nextElementSibling;
    }
    return modifiedRoot;
}

export function isListItem(node) {
    return node.nodeName === "LI" && !node.classList.contains("nav-item");
}
