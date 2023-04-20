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
        // Don't serialize transient nodes
        if (!["true", ""].includes(node.dataset.oeTransientContent)) {
            while (child) {
                if (!nodesToStripFromChildren.has(child.oid)) {
                    result.children.push(serializeNode(child, nodesToStripFromChildren));
                }
                child = child.nextSibling;
            }
        }
    }
    return result;
}

export function unserializeNode(obj) {
    let result = undefined;
    if (obj.nodeType === Node.TEXT_NODE) {
        result = document.createTextNode(obj.textValue);
    } else if (obj.nodeType === Node.ELEMENT_NODE) {
        result = document.createElement(obj.tagName);
        for (const key in obj.attributes) {
            result.setAttribute(key, obj.attributes[key]);
        }
        obj.children.forEach(child => result.append(unserializeNode(child)));
    } else {
        console.warn('unknown node type');
    }
    result.oid = obj.oid;
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
