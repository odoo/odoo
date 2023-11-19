export function getContent(node) {
    const selection = node.ownerDocument.getSelection();
    return _getElemContent(node, selection);
}

function _getContent(node, selection) {
    switch (node.nodeType) {
        case Node.TEXT_NODE:
            return getTextContent(node, selection);
        case Node.ELEMENT_NODE:
            return getElemContent(node, selection);
        case Node.COMMENT_NODE:
            return `<!--${node.textContent}-->`;
        default:
            throw new Error("boom");
    }
}

function getTextContent(node, selection) {
    let text = node.textContent;
    if (selection.focusNode === node) {
        text = text.slice(0, selection.focusOffset) + "]" + text.slice(selection.focusOffset);
    }
    if (selection.anchorNode === node) {
        const isAfterFocus =
            selection.focusNode === selection.anchorNode &&
            selection.focusOffset < selection.anchorOffset;
        const idx = selection.anchorOffset + (isAfterFocus ? 1 : 0);
        text = text.slice(0, idx) + "[" + text.slice(idx);
    }
    return text.replace(/\u00a0/g, "&nbsp;");
}

const VOID_ELEMS = new Set(["BR", "IMG", "INPUT", "HR"]);

function _getElemContent(el, selection) {
    let result = "";
    function addTextSelection() {
        if (selection.anchorNode === el && index === selection.anchorOffset) {
            result += "[";
        }
        if (selection.focusNode === el && index === selection.focusOffset) {
            result += "]";
        }
    }
    let index = 0;
    for (const child of el.childNodes) {
        addTextSelection();
        result += _getContent(child, selection);
        index++;
    }
    addTextSelection();
    return result;
}

function getElemContent(el, selection) {
    const tag = el.tagName.toLowerCase();
    const attrs = [];
    for (const attr of el.attributes) {
        attrs.push(`${attr.name}="${attr.value}"`);
    }
    const attrStr = (attrs.length ? " " : "") + attrs.join(" ");
    return VOID_ELEMS.has(el.tagName)
        ? `<${tag + attrStr}>`
        : `<${tag + attrStr}>${_getElemContent(el, selection)}</${tag}>`;
}

function getTextNodesIterator(el) {
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    walker[Symbol.iterator] = () => ({
        next() {
            const value = walker.nextNode();
            return { value, done: !value };
        },
    });
    return walker;
}

export function setContent(el, content) {
    // build a temp div element to first remove all [] characters in text nodes
    const div = document.createElement("div");
    div.innerHTML = content;
    for (const textNode of getTextNodesIterator(div)) {
        textNode.textContent = textNode.textContent.replace("[", "").replace("]", "");
    }
    // remove extra empty text nodes
    el.innerHTML = div.innerHTML;

    const configSelection = getSelection(el, content);
    if (configSelection) {
        setSelection(configSelection);
    }
    if (getContent(el) !== content) {
        throw new Error("error in setContent/getContent helpers");
    }
}

export function setSelection({ anchorNode, anchorOffset, focusNode, focusOffset }) {
    const selection = anchorNode.ownerDocument.getSelection();
    selection.setBaseAndExtent(anchorNode, anchorOffset, focusNode, focusOffset);
}

export function getSelection(el, content) {
    if (content.indexOf("[") === -1 || content.indexOf("]") === -1) {
        return;
    }

    const elRef = document.createElement(el.tagName);
    elRef.innerHTML = content;

    const configSelection = {};
    visitAndSetRange(el, elRef, configSelection);

    if (configSelection.anchorNode === undefined || configSelection.focusNode === undefined) {
        return;
    }
    return configSelection;
}

export function setRange(el, content) {
    // sanity check
    const rawContent = content.replace("[", "").replace("]", "");
    if (el.innerHTML !== rawContent) {
        throw new Error("setRange requires the same html content");
    }

    // create range
    const range = document.createRange();
    const elRef = document.createElement(el.tagName);
    elRef.innerHTML = content;

    visitAndSetRange(el, elRef, range);

    // set selection range
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
}

function visitAndSetRange(target, ref, configSelection) {
    function applyRange(target, ref, idx) {
        const text = ref.textContent;
        if (text.includes("[")) {
            const index = idx === undefined ? text.replace("]", "").indexOf("[") : idx;
            configSelection.anchorNode = target;
            configSelection.anchorOffset = index;
        }
        if (text.includes("]")) {
            const index = idx === undefined ? text.replace("[", "").indexOf("]") : idx;
            configSelection.focusNode = target;
            configSelection.focusOffset = index;
        }
    }

    if (target.nodeType === Node.TEXT_NODE) {
        applyRange(target, ref);
    } else {
        const targetChildren = [...target.childNodes];
        const refChildren = [...ref.childNodes];
        let i = 0;
        let j = 0;
        while (i !== targetChildren.length || j !== refChildren.length) {
            const targetChild = targetChildren[i] || targetChildren[i - 1];
            const refChild = refChildren[j];
            if (!targetChild) {
                applyRange(target, refChild, 0);
                return;
            }
            if (refChild.nodeType === targetChild.nodeType) {
                visitAndSetRange(targetChild, refChild, configSelection);
                i++;
                j++;
            } else {
                // refchild is a textnode reduced to "[" or "]"
                j++;
                applyRange(target, refChild, i);
            }
        }
    }
}
