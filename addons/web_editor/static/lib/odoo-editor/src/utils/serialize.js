/** @odoo-module **/
// TODO: avoid empty keys when not necessary to reduce request size
export function serializeNode(node, nodesToStripFromChildren = new Set()) {
    let result = {
        nodeType: node.nodeType,
        oid: node.oid,
    };
    if (!node.oid) {
        throw new Error('node.oid can not be falsy.');
    }
    if (node.nodeType === Node.TEXT_NODE) {
        result.textValue = node.nodeValue;
    } else if (node.nodeType === Node.ELEMENT_NODE) {
        result.tagName = node.tagName;
        result.children = [];
        result.attributes = {};
        for (let i = 0; i < node.attributes.length; i++) {
            result.attributes[node.attributes[i].name] = node.attributes[i].value;
        }
        let child = node.firstChild;
        while (child) {
            if (!nodesToStripFromChildren.has(child.oid)) {
                result.children.push(serializeNode(child, nodesToStripFromChildren));
            }
            child = child.nextSibling;
        }
    }
    return result;
}

/**
 * @param {Object} node Serialized node.
 * @param {Map} idToNodeMap optional - Map to reference every unserialized
 *              node from its oid.
 * @returns {Node}
 */
export function unserializeNode(obj, idToNodeMap, store=false) {
    let result = idToNodeMap && idToNodeMap.get(obj.oid);
    if (obj.nodeType === Node.TEXT_NODE) {
        if (result) {
            if (result.textContent !== obj.textValue) {
                result.textContent = obj.textValue;
            }
        } else {
            result = document.createTextNode(obj.textValue);
        }
    } else if (obj.nodeType === Node.ELEMENT_NODE) {
        result = result || document.createElement(obj.tagName);
        for (const key in obj.attributes) {
            if (result.getAttribute(key) !== obj.attributes[key]) {
                result.setAttribute(key, obj.attributes[key]);
            }
        }
        const children = obj.children.map(child => unserializeNode(child, idToNodeMap, store));
        const childrenSet = new Set(children);
        for (const currentChild of Array.from(result.childNodes)) {
            if (!childrenSet.has(currentChild)) {
                currentChild.remove();
            }
        }
        let index = 0;
        for (const child of children) {
            if (child !== result.childNodes.item(index)) {
                const currentChild = result.childNodes.item(index);
                if (!currentChild) {
                    result.append(child);
                } else {
                    currentChild.before(child);
                }
            }
            index++;
        }
    } else {
        console.warn('unknown node type');
    }
    result.oid = obj.oid;
    if (store && idToNodeMap) {
        idToNodeMap.set(result.oid, result);
    }
    return result;
}

export function serializeSelection(selection) {
    if (
        selection &&
        selection.anchorNode &&
        selection.anchorNode.oid &&
        typeof selection.anchorOffset !==  'undefined' &&
        selection.focusNode &&
        selection.anchorNode.oid &&
        typeof selection.focusOffset !==  'undefined'
    ) {
        return {
            anchorNodeOid: selection.anchorNode.oid,
            anchorOffset: selection.anchorOffset,
            focusNodeOid: selection.focusNode.oid,
            focusOffset: selection.focusOffset,
        };
    } else {
        return {
            anchorNodeOid: undefined,
            anchorOffset: undefined,
            focusNodeOid: undefined,
            focusOffset: undefined,
        };
    }
}
