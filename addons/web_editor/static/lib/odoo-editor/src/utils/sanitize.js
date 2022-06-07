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
    isUnremovable
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
    if (node.tagName === 'LI' && node.classList.contains('oe-nested')) {
        return (
            node.lastElementChild &&
            node2.firstElementChild &&
            getListMode(node.lastElementChild) === getListMode(node2.firstElementChild)
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
        const rootClosestBlock = closestBlock(root);
        if (rootClosestBlock) {
            // Remove unique ids from checklists and stars. These will be
            // renewed afterwards.
            for (const node of rootClosestBlock.querySelectorAll('[id^=checkId-]')) {
                node.removeAttribute('id');
            }
        }
        this.parse(root);
        if (rootClosestBlock) {
            // Ensure unique ids on checklists and stars.
            for (const node of rootClosestBlock.querySelectorAll('.o_checklist > li, .o_stars')) {
                node.setAttribute('id', `checkId-${Math.floor(new Date() * Math.random())}`);
            }
        }
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
            const restoreCursor = node.isConnected && preserveCursor(this.root.ownerDocument);
            const nodeP = node.previousSibling;
            moveNodes(...endPos(node.previousSibling), node);
            if (restoreCursor) {
                restoreCursor();
            };
            node = nodeP;
        }

        // Remove zero-width spaces added by `fillEmpty` when there is content
        // and the selection is not next to it.
        const anchor = this.root.ownerDocument.getSelection().anchorNode;
        if (
            node.nodeType === Node.TEXT_NODE &&
            node.textContent.includes('\u200B') &&
            (
                node.textContent.length > 1 ||
                // There can be multiple ajacent text nodes, in which case the
                // zero-width space is not needed either, despite being alone
                // (length === 1) in its own text node.
                Array.from(node.parentNode.childNodes).find(
                    sibling =>
                        sibling !== node &&
                        sibling.nodeType === Node.TEXT_NODE &&
                        sibling.length > 0
                )
            ) &&
            !isBlock(node.parentElement) &&
            anchor !== node
        ) {
            const restoreCursor = node.isConnected && preserveCursor(this.root.ownerDocument);
            node.textContent = node.textContent.replace('\u200B', '');
            node.parentElement.removeAttribute("data-oe-zws-empty-inline");
            if (restoreCursor) {
                restoreCursor();
            };
        }

        // Remove empty blocks in <li>
        if (node.nodeName === 'P' && node.parentElement.tagName === 'LI') {
            const next = node.nextSibling;
            const pnode = node.parentElement;
            if (isEmptyBlock(node)) {
                const restoreCursor = node.isConnected && preserveCursor(this.root.ownerDocument);
                node.remove();
                fillEmpty(pnode);
                this._parse(next);
                if (restoreCursor) {
                    restoreCursor(new Map([[node, pnode]]));
                };
                return;
            }
        }
        // Transform <li> into <p> if they are not in a <ul> / <ol>
        if (node.nodeName === 'LI' && !node.closest('ul, ol')) {
            const p = document.createElement("p");
            p.replaceChildren(...node.childNodes);
            node.replaceWith(p);
            node = p;
        }

        // Sanitize font awesome elements
        if (isFontAwesome(node)) {
            // Ensure a zero width space is present inside the FA element.
            if (node.innerHTML !== '\u200B') node.innerHTML = '&#x200B;';
        }

        // Sanitize media elements
        if (isMediaElement(node) || node.tagName === 'HR') {
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
