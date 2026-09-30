/**
 * Calls the given `func` then returns/resolves to `true`
 * if it will result to unloading of the page.
 * @param {(...args: any[]) => void} func
 * @param  {any[]} args
 * @returns {boolean | Promise<boolean>}
 */
export function callWithUnloadCheck(func, ...args) {
    let willUnload = false;
    const beforeunload = () => (willUnload = true);
    window.addEventListener("beforeunload", beforeunload);
    const result = func(...args);
    if (result instanceof Promise) {
        return result.then(() => {
            window.removeEventListener("beforeunload", beforeunload);
            return willUnload;
        });
    } else {
        window.removeEventListener("beforeunload", beforeunload);
        return willUnload;
    }
}

function formatValue(key, value, maxLength = 200) {
    if (!value) {
        return "(empty)";
    }
    return value.length > maxLength ? value.slice(0, maxLength) + "..." : value;
}

function serializeNode(node) {
    if (node.nodeType === Node.TEXT_NODE) {
        return `"${node.nodeValue.trim()}"`;
    }
    return node.outerHTML ? formatValue("node", node.outerHTML, 500) : "[Unknown Node]";
}

export function serializeChanges(snapshot, current) {
    const changes = {
        node: serializeNode(current),
    };
    function pushChanges(key, obj) {
        changes[key] = changes[key] || [];
        changes[key].push(obj);
    }

    if (snapshot.textContent !== current.textContent) {
        pushChanges("modifiedText", { before: snapshot.textContent, after: current.textContent });
    }

    const oldChildren = [...snapshot.childNodes].filter((node) => node.nodeType !== Node.TEXT_NODE);
    const newChildren = [...current.childNodes].filter((node) => node.nodeType !== Node.TEXT_NODE);
    oldChildren.forEach((oldNode, index) => {
        if (!newChildren[index] || !oldNode.isEqualNode(newChildren[index])) {
            pushChanges("removedNodes", { oldNode: serializeNode(oldNode) });
        }
    });
    newChildren.forEach((newNode, index) => {
        if (!oldChildren[index] || !newNode.isEqualNode(oldChildren[index])) {
            pushChanges("addedNodes", { newNode: serializeNode(newNode) });
        }
    });

    const oldAttrNames = new Set([...snapshot.attributes].map((attr) => attr.name));
    const newAttrNames = new Set([...current.attributes].map((attr) => attr.name));
    new Set([...oldAttrNames, ...newAttrNames]).forEach((attributeName) => {
        const oldValue = snapshot.getAttribute(attributeName);
        const newValue = current.getAttribute(attributeName);
        const before = oldValue !== newValue || !newAttrNames.has(attributeName) ? oldValue : null;
        const after = oldValue !== newValue || !oldAttrNames.has(attributeName) ? newValue : null;
        if (before || after) {
            pushChanges("modifiedAttributes", { attributeName, before, after });
        }
    });
    return changes;
}

export function serializeMutation(mutation) {
    const { type, attributeName } = mutation;
    if (type === "attributes" && attributeName) {
        return `attribute: ${attributeName}`;
    } else {
        return type;
    }
}

/**
 * @param {HTMLElement} element
 * @returns {HTMLElement | null}
 */
export function getScrollParent(element) {
    if (!element) {
        return null;
    }
    // We cannot only rely on the fact that the element’s scrollHeight is
    // greater than its clientHeight. This might not be the case when a step
    // starts, and the scrollbar could appear later. For example, when clicking
    // on a "building block" in the "building block previews modal" during a
    // tour (in website edit mode). When the modal opens, not all "building
    // blocks" are loaded yet, and the scrollbar is not present initially.
    const overflowY = window.getComputedStyle(element).overflowY;
    const isScrollable =
        overflowY === "auto" ||
        overflowY === "scroll" ||
        (overflowY === "visible" && element === element.ownerDocument.scrollingElement);
    if (isScrollable) {
        return element;
    } else {
        return getScrollParent(element.parentNode);
    }
}
