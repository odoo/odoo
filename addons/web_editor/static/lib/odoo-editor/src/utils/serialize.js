/** @odoo-module **/

import { getCursorDirection } from './utils';

// TODO: avoid empty keys when not necessary to reduce request size
export function nodeToObject(node, nodesToStripFromChildren = new Set()) {
    let result = {
        nodeType: node.nodeType,
        oid: node.oid,
    };
    if (!node.oid) {
        console.warn('OID can not be falsy!');
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
                result.children.push(nodeToObject(child, nodesToStripFromChildren));
            }
            child = child.nextSibling;
        }
    }
    return result;
}

export function objectToNode(obj) {
    let result = undefined;
    if (obj.nodeType === Node.TEXT_NODE) {
        result = document.createTextNode(obj.textValue);
    } else if (obj.nodeType === Node.ELEMENT_NODE) {
        result = document.createElement(obj.tagName);
        for (const key in obj.attributes) {
            result.setAttribute(key, obj.attributes[key]);
        }
        obj.children.forEach(child => result.append(objectToNode(child)));
    } else {
        console.warn('unknown node type');
    }
    result.oid = obj.oid;
    return result;
}

export function selectionToObject(selection) {
    const range = selection.getRangeAt(0);
    return {
        range: {
            startContainer: range.startContainer.oid,
            endContainer: range.endContainer.oid,
            startOffset: range.startOffset,
            endOffset: range.endOffset,
        },
        direction: getCursorDirection(
            selection.anchorNode,
            selection.anchorOffset,
            selection.focusNode,
            selection.focusOffset,
        ),
    };
}

export function objectToRange(obj, idFind, doc = document) {
    const range = doc.createRange();
    range.setStart(idFind(obj.startContainer), obj.startOffset);
    range.setEnd(idFind(obj.endContainer), obj.endOffset);
    return range;
}
