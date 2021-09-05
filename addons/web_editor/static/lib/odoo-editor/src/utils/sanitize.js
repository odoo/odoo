/** @odoo-module **/
import {
    closestBlock,
    endPos,
    fillEmpty,
    getListMode,
    isBlock,
    isEmptyBlock,
    isVisibleEmpty,
    moveNodes,
    preserveCursor,
    isFontAwesome,
    isMediaElement,
    getDeepRange,
    isUnbreakable,
} from './utils.js';

const NOT_A_NUMBER = /[^\d]/g;
export function areSimilarElements(node, node2) {
    if (
        !node ||
        !node2 ||
        node.nodeType !== Node.ELEMENT_NODE ||
        node2.nodeType !== Node.ELEMENT_NODE
    ) {
        return false;
    }
    if (node.tagName !== node2.tagName) {
        return false;
    }
    for (const att of node.attributes) {
        const att2 = node2.attributes[att.name];
        if ((att2 && att2.value) !== att.value) {
            return false;
        }
    }
    for (const att of node2.attributes) {
        const att2 = node.attributes[att.name];
        if ((att2 && att2.value) !== att.value) {
            return false;
        }
    }
    function isNotNoneValue(value) {
        return value && value !== 'none';
    }
    if (
        isNotNoneValue(getComputedStyle(node, ':before').getPropertyValue('content')) ||
        isNotNoneValue(getComputedStyle(node, ':after').getPropertyValue('content')) ||
        isNotNoneValue(getComputedStyle(node2, ':before').getPropertyValue('content')) ||
        isNotNoneValue(getComputedStyle(node2, ':after').getPropertyValue('content'))
    ) {
        return false;
    }
    if (node.tagName == 'LI' && node.classList.contains('oe-nested')) {
        return (
            node.lastElementChild &&
            node2.firstElementChild &&
            getListMode(node.lastElementChild) == getListMode(node2.firstElementChild)
        );
    }
    if (['UL', 'OL'].includes(node.tagName)) {
        return !isVisibleEmpty(node) && !isVisibleEmpty(node2);
    }
    if (isBlock(node) || isVisibleEmpty(node) || isVisibleEmpty(node2)) {
        return false;
    }
    const nodeStyle = getComputedStyle(node);
    const node2Style = getComputedStyle(node2);
    return (
        !+nodeStyle.padding.replace(NOT_A_NUMBER, '') &&
        !+node2Style.padding.replace(NOT_A_NUMBER, '') &&
        !+nodeStyle.margin.replace(NOT_A_NUMBER, '') &&
        !+node2Style.margin.replace(NOT_A_NUMBER, '')
    );
}

class Sanitize {
    constructor(root) {
        this.root = root;
        this.parse(root);
    }

    parse(node) {
        node = closestBlock(node);
        if (['UL', 'OL'].includes(node.tagName)) {
            node = node.parentElement;
        }
        this._parse(node);
    }

    _parse(node) {
        if (!node) {
            return;
        }

        // Merge identical elements together
        while (areSimilarElements(node, node.previousSibling) && !isUnbreakable(node)) {
            getDeepRange(this.root, { select: true });
            const restoreCursor = preserveCursor(this.root.ownerDocument);
            const nodeP = node.previousSibling;
            moveNodes(...endPos(node.previousSibling), node);
            restoreCursor();
            node = nodeP;
        }

        // Remove empty blocks in <li>
        if (node.nodeName == 'P' && node.parentElement.tagName == 'LI') {
            const next = node.nextSibling;
            const pnode = node.parentElement;
            if (isEmptyBlock(node)) {
                const restoreCursor = preserveCursor(this.root.ownerDocument);
                node.remove();
                fillEmpty(pnode);
                this._parse(next);
                restoreCursor(new Map([[node, pnode]]));
                return;
            }
        }

        // Sanitize font awesome elements
        if (isFontAwesome(node)) {
            // Ensure a zero width space is present inside the FA element.
            if (node.innerHTML !== '\u200B') node.innerHTML = '&#x200B;';
        }

        // Sanitize media elements
        if (isMediaElement(node)) {
            // Ensure all media elements are tagged contenteditable=false.
            // we cannot use the node.isContentEditable because it can wrongly return false
            // when the editor is starting up ( first sanitize )
            if (node.getAttribute('contenteditable') !== 'false') {
                node.setAttribute('contenteditable', 'false');
            }
        }

        // FIXME not parse out of editable zone...
        this._parse(node.firstChild);
        this._parse(node.nextSibling);
    }
}

export function sanitize(root) {
    new Sanitize(root);
    return root;
}
