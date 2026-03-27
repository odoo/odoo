const RSTRIP_REGEXP = /(?=\n[ \t]*$)/;

let translationContext = null;

const TCTX = "t-translation-context";

/**
 * @param {Node} node
 */
function getTranslationContext(node) {
    if (node.hasAttribute(TCTX)) {
        return node.getAttribute(TCTX);
    }
    return getTranslationContext(node.parentElement);
}

const contextByTextNode = new Map();

/**
 * @param {Node} node
 */
function setTranslationContext(node) {
    switch (node.nodeType) {
        case Node.TEXT_NODE:
            if (node.nodeValue.trim() != "") {
                contextByTextNode.set(node, translationContext);
            }
            break;
        case Node.ELEMENT_NODE:
            node.setAttribute(TCTX, translationContext);
            break;
    }
}

export function applyContextToTextNode() {
    for (const [textNode, context] of contextByTextNode) {
        const wrapper = document.createElement("t");
        wrapper.setAttribute(TCTX, context);
        textNode.before(wrapper);
        wrapper.appendChild(textNode);
    }
    contextByTextNode.clear();
}

/**
 * @param {Node} node
 */
export function deepClone(node) {
    const clone = node.cloneNode();
    if (node.nodeType === Node.TEXT_NODE) {
        if (contextByTextNode.has(node)) {
            contextByTextNode.set(clone, contextByTextNode.get(node));
        }
    }
    if (node.childNodes?.length) {
        for (const childNode of [...node.childNodes]) {
            clone.append(deepClone(childNode));
        }
    }
    return clone;
}

/**
 * The child nodes of operation represent new content to create before target or
 * or other elements to move before target from the target tree (tree from which target is part of).
 * Some processing of text nodes has to be done in order to normalize the situation.
 * Note: we assume that target has a parent element.
 * @param {Element} target
 * @param {Element} operation
 */
function addBefore(target, operation) {
    const nodes = getNodes(target, operation);
    if (nodes.length === 0) {
        return;
    }
    const { previousSibling } = target;
    target.before(...nodes);
    if (previousSibling?.nodeType === Node.TEXT_NODE) {
        const [text1, text2] = previousSibling.data.split(RSTRIP_REGEXP);
        previousSibling.data = text1.trimEnd();
        if (text2 && nodes.some((n) => n.nodeType !== Node.TEXT_NODE)) {
            const textNode = document.createTextNode(text2);
            target.before(textNode);
            if (textNode.previousSibling.nodeType === Node.TEXT_NODE) {
                textNode.previousSibling.data = textNode.previousSibling.data.trimEnd();
            }
        }
    }
}

/**
 * element is part of a tree. Here we return the root element of that tree.
 * Note: this root element is not necessarily the documentElement of the ownerDocument
 * of element (hence the following code).
 * @param {Element} element
 * @returns {Element}
 */
function getRoot(element) {
    while (element.parentElement) {
        element = element.parentElement;
    }
    return element;
}

const HASCLASS_REGEXP = /hasclass\(([^)]*)\)/g;
const CLASS_CONTAINS_REGEX = /contains\(@class.*\)/g;
/**
 * @param {Element} operation
 * @returns {string}
 */
function getXpath(operation) {
    const xpath = operation.getAttribute("expr");
    if (odoo.debug) {
        if (CLASS_CONTAINS_REGEX.test(xpath)) {
            const parent = operation.closest("t[t-inherit]");
            const templateName = parent.getAttribute("t-name") || parent.getAttribute("t-inherit");
            console.warn(
                `Error-prone use of @class in template "${templateName}" (or one of its inheritors).` +
                    " Use the hasclass(*classes) function to filter elements by their classes"
            );
        }
    }
    // hasclass does not exist in XPath 1.0 but is a custom function defined server side (see _hasclass) usable in lxml.
    // Here we have to replace it by a complex condition (which is not nice).
    // Note: we assume that classes do not contain the 2 chars , and )
    return xpath.replaceAll(HASCLASS_REGEXP, (_, capturedGroup) =>
        capturedGroup
            .split(",")
            .map((c) => `contains(concat(' ', @class, ' '), ' ${c.trim().slice(1, -1)} ')`)
            .join(" and ")
    );
}

/**
 * @param {Element} element
 * @param {Element} operation
 * @returns {Node|null}
 */
function getNode(element, operation) {
    const root = getRoot(element);
    const doc = new Document();
    doc.appendChild(root); // => root is the documentElement of its ownerDocument (we do that in case root is a clone)
    if (operation.tagName === "xpath") {
        const xpath = getXpath(operation);
        const result = doc.evaluate(xpath, root, null, XPathResult.FIRST_ORDERED_NODE_TYPE);
        return result.singleNodeValue;
    }
    const attributes = [...operation.attributes].filter((attr) => !attr.name.startsWith(TCTX));
    for (const elem of root.querySelectorAll(operation.tagName)) {
        if (
            attributes.every(
                ({ name, value }) => name === "position" || elem.getAttribute(name) === value
            )
        ) {
            return elem;
        }
    }
    return null;
}

/**
 * @param {Element} element
 * @param {Element} operation
 * @returns {Element}
 */
function getElement(element, operation) {
    const node = getNode(element, operation);
    if (!node) {
        throw new Error(`Element '${operation.outerHTML}' cannot be located in element tree`);
    }
    if (!(node instanceof Element)) {
        throw new Error(`Found node ${node} instead of an element`);
    }
    return node;
}

/**
 * @param {Element} element
 * @param {Element} operation
 * @returns {Node[]}
 */
function getNodes(element, operation) {
    const nodes = [];
    for (const childNode of operation.childNodes) {
        if (childNode.tagName === "xpath" && childNode.getAttribute?.("position") === "move") {
            const node = getElement(element, childNode);
            node.setAttribute(TCTX, getTranslationContext(node));
            removeNode(node);
            nodes.push(node);
        } else {
            setTranslationContext(childNode);
            nodes.push(childNode);
        }
    }
    return nodes;
}

function splitAndTrim(str, separator) {
    return str.split(separator).map((s) => s.trim());
}

/**
 * @param {Element} target
 * @param {Element} operation
 */
function modifyAttributes(target, operation) {
    for (const child of operation.children) {
        if (child.tagName !== "attribute") {
            continue;
        }
        const attributeName = child.getAttribute("name");
        const firstNode = child.childNodes[0];
        let value = firstNode?.nodeType === Node.TEXT_NODE ? firstNode.data : "";

        const add = child.getAttribute("add") || "";
        const remove = child.getAttribute("remove") || "";
        if (add || remove) {
            if (firstNode?.nodeType === Node.TEXT_NODE) {
                throw new Error(`Useless element content ${firstNode.outerHTML}`);
            }
            const separator = child.getAttribute("separator") || ",";
            const toRemove = new Set(splitAndTrim(remove, separator));
            const values = splitAndTrim(target.getAttribute(attributeName) || "", separator).filter(
                (s) => !toRemove.has(s)
            );
            values.push(...splitAndTrim(add, separator).filter((s) => s));
            value = values.join(separator);
        }

        if (value) {
            target.setAttribute(attributeName, value);
            if (!(add || remove)) {
                target.setAttribute(`t-translation-context-${attributeName}`, translationContext);
            }
        } else {
            target.removeAttribute(attributeName);
        }
    }
}

/**
 * Remove node and normalize surrounind text nodes (if any)
 * Note: we assume that node has a parent element
 * @param {Node} node
 */
function removeNode(node) {
    const { nextSibling, previousSibling } = node;
    node.remove();
    if (
        nextSibling?.nodeType === Node.TEXT_NODE &&
        previousSibling?.nodeType === Node.TEXT_NODE &&
        previousSibling.parentElement.firstChild === previousSibling
    ) {
        previousSibling.data = previousSibling.data.trimEnd();
    }
}

/**
 * @param {Element} root
 * @param {Element} target
 * @param {Element} operation
 */
function replace(root, target, operation) {
    const mode = operation.getAttribute("mode") || "outer";
    switch (mode) {
        case "outer": {
            const result = operation.ownerDocument.evaluate(
                ".//*[text()='$0']",
                operation,
                null,
                XPathResult.ORDERED_NODE_SNAPSHOT_TYPE
            );
            target.setAttribute(TCTX, getTranslationContext(target));
            for (let i = 0; i < result.snapshotLength; i++) {
                const loc = result.snapshotItem(i);
                loc.firstChild.replaceWith(deepClone(target));
            }
            if (target.parentElement) {
                const nodes = getNodes(target, operation);
                target.replaceWith(...nodes);
            } else {
                let operationContent = null;
                let comment = null;
                for (const child of operation.childNodes) {
                    if (child.nodeType === Node.ELEMENT_NODE) {
                        setTranslationContext(child);
                        operationContent = child;
                        break;
                    }
                    if (child.nodeType === Node.COMMENT_NODE) {
                        comment = child;
                    }
                }
                root = deepClone(operationContent);
                if (target.hasAttribute("t-name")) {
                    root.setAttribute("t-name", target.getAttribute("t-name"));
                }
                if (comment) {
                    root.prepend(comment);
                }
            }
            break;
        }
        case "inner":
            while (target.firstChild) {
                target.removeChild(target.lastChild);
            }
            for (const node of [...operation.childNodes]) {
                setTranslationContext(node);
                target.append(node);
            }
            break;
        default:
            throw new Error(`Invalid mode attribute: '${mode}'`);
    }
    return root;
}

/**
 * @param {Element} root
 * @param {Element} operations is a single element whose children represent operations to perform on root
 * @param {string} [url=""]
 * @returns {Element} root modified (in place) by the operations
 */
export function applyInheritance(root, operations, url = "") {
    translationContext = url.split("/")[1] ?? ""; // use addon name as context
    for (const operation of operations.children) {
        const target = getElement(root, operation);
        const position = operation.getAttribute("position") || "inside";

        if (odoo.debug && url) {
            const attributes = [...operation.attributes].map(
                ({ name, value }) =>
                    `${name}=${JSON.stringify(name === "position" ? position : value)}`
            );
            const comment = document.createComment(
                ` From file: ${url} ; ${attributes.join(" ; ")} `
            );
            if (position === "attributes") {
                target.before(comment); // comment won't be visible if target is root
            } else {
                operation.prepend(comment);
            }
        }

        switch (position) {
            case "replace": {
                root = replace(root, target, operation); // root can be replaced (see outer mode)
                break;
            }
            case "attributes": {
                modifyAttributes(target, operation);
                break;
            }
            case "inside": {
                const sentinel = document.createElement("sentinel");
                target.append(sentinel);
                addBefore(sentinel, operation);
                removeNode(sentinel);
                break;
            }
            case "after": {
                const sentinel = document.createElement("sentinel");
                target.after(sentinel);
                addBefore(sentinel, operation);
                removeNode(sentinel);
                break;
            }
            case "before": {
                addBefore(target, operation);
                break;
            }
            default:
                throw new Error(`Invalid position attribute: '${position}'`);
        }
    }
    translationContext = null;
    return root;
}
