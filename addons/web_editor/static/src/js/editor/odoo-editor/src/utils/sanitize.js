/** @odoo-module **/
import {
    closestBlock,
    closestElement,
    startPos,
    fillEmpty,
    getListMode,
    isBlock,
    isEmptyBlock,
    isSelfClosingElement,
    moveNodes,
    preserveCursor,
    isFontAwesome,
    getDeepRange,
    isUnbreakable,
    isEditorTab,
    isProtected,
    isZWS,
    getUrlsInfosInString,
    isArtificialVoidElement,
    ancestors,
} from './utils.js';

const NOT_A_NUMBER = /[^\d]/g;

function hasPseudoElementContent (node, pseudoSelector) {
    const content = getComputedStyle(node, pseudoSelector).getPropertyValue('content');
    return content && content !== 'none';
}

export function areSimilarElements(node, node2) {
    if (![node, node2].every(n => n?.nodeType === Node.ELEMENT_NODE)) {
        return false; // The nodes don't both exist or aren't both elements.
    }
    if (node.nodeName !== node2.nodeName) {
        return false; // The nodes aren't the same type of element.
    }
    const nodeName = node.nodeName;

    for (const name of new Set([
        ...node.getAttributeNames(),
        ...node2.getAttributeNames(),
    ])) {
        if (node.getAttribute(name) !== node2.getAttribute(name)) {
            return false; // The nodes don't have the same attributes.
        }
    }
    if ([node, node2].some(n => hasPseudoElementContent(n, ':before') || hasPseudoElementContent(n, ':after'))) {
        return false; // The nodes have pseudo elements with content.
    }
    if (nodeName === 'LI' && node.classList.contains('oe-nested')) {
        // If the nodes are adjacent nested list items, we need to compare the
        // types of their "adjacent" list children rather that the list items
        // themselves.
        return (
            node.lastElementChild &&
            node2.firstElementChild &&
            getListMode(node.lastElementChild) === getListMode(node2.firstElementChild)
        );
    }
    if (['UL', 'OL'].includes(nodeName)) {
        return !isSelfClosingElement(node) && !isSelfClosingElement(node2); // The nodes are non-empty lists. TODO: this doesn't check that and it will always be true!
    }
    if (isBlock(node) || isSelfClosingElement(node) || isSelfClosingElement(node2)) {
        return false; // The nodes are blocks or are empty but visible. TODO: Not sure this was what we wanted to check (see just above).
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

/**
 * Sanitize the given node and return it.
 *
 * @param {Node} node
 * @param {Element} root
 * @returns {Node} the sanitized node
 */
function sanitizeNode(node, root) {
    // First ensure elements which should not contain any content are tagged
    // contenteditable=false to avoid any hiccup.
    if (isArtificialVoidElement(node) && node.getAttribute('contenteditable') !== 'false') {
        node.setAttribute('contenteditable', 'false');
    }

    if (
        areSimilarElements(node, node.previousSibling) &&
        !isUnbreakable(node) &&
        !isEditorTab(node) &&
        !(
            node.attributes?.length === 1 &&
            node.hasAttribute('data-oe-zws-empty-inline') &&
            (node.textContent === '\u200B' || node.previousSibling.textContent === '\u200B'))
    ) {
        // Merge identical elements together.
        getDeepRange(root, { select: true });
        const restoreCursor = node.isConnected && preserveCursor(root.ownerDocument);
        moveNodes(...startPos(node), node.previousSibling);
        restoreCursor?.();
    } else if (node.nodeType === Node.COMMENT_NODE) {
        // Remove comment nodes to avoid issues with mso comments.
        const parent = node.parentElement;
        node.remove();
        node = parent; // The node has been removed, update the reference.
    } else if (
        node.nodeName === 'P' && // Note: not sure we should limit to <p>.
        node.parentElement.nodeName === 'LI' &&
        isEmptyBlock(node)
    ) {
        // Remove empty paragraphs in <li>.
        const parent = node.parentElement;
        const restoreCursor = node.isConnected && preserveCursor(root.ownerDocument);
        node.remove();
        fillEmpty(parent);
        restoreCursor?.(new Map([[node, parent]]));
        node = parent; // The node has been removed, update the reference.
    } else if (node.nodeName === 'LI' && !node.closest('ul, ol')) {
        // Transform <li> into <p> if they are not in a <ul> / <ol>.
        const paragraph = document.createElement('p');
        paragraph.replaceChildren(...node.childNodes);
        node.replaceWith(paragraph);
        node = paragraph; // The node has been removed, update the reference.
    } else if (isFontAwesome(node) && node.textContent !== '\u200B') {
        // Ensure a zero width space is present inside the FA element.
        node.textContent = '\u200B';
    } else if (isEditorTab(node)) {
        // Ensure the editor tabs align on a 40px grid.
        let tabPreviousSibling = node.previousSibling;
        while (isZWS(tabPreviousSibling)) {
            tabPreviousSibling = tabPreviousSibling.previousSibling;
        }
        if (isEditorTab(tabPreviousSibling)) {
            node.style.width = '40px';
        } else {
            const editable = closestElement(node, '.odoo-editor-editable');
            if (editable?.firstElementChild) {
                const nodeRect = node.getBoundingClientRect();
                const referenceRect = editable.firstElementChild.getBoundingClientRect();
                // Values from getBoundingClientRect() are all zeros during
                // Editor startup or saving. We cannot recalculate the tabs
                // width in thoses cases.
                if (nodeRect.width && referenceRect.width) {
                    const width = (nodeRect.left - referenceRect.left) % 40;
                    node.style.width = (40 - width) + 'px';
                }
            }
        }
    }
    return node;
}

/**
 * Sanitize a node tree and return the sanitized node.
 *
 * @param {Node} nodeToSanitize the node to sanitize
 * @param {Node} [root] the root of the tree to sanitize (will not sanitize nodes outside of this tree)
 * @returns {Node} the sanitized node
 */
export function sanitize(nodeToSanitize, root = nodeToSanitize) {
    const start = nodeToSanitize.ownerDocument.getSelection()?.anchorNode;
    const block = closestBlock(nodeToSanitize);
    if (block && root.contains(block)) {
        // If the node is a list, start sanitization from its parent to ensure
        // adjacent lists are merged when needed.
        const isList = ['UL', 'OL'].includes(block.nodeName);
        let node = isList ? block.parentElement : block;

        // Sanitize the tree.
        while (node?.isConnected && root.contains(node)) {
            if (!isProtected(node)) {
                node = sanitizeNode(node, root); // The node itself might be replaced during sanitization.
            }
            node = node.firstChild || node.nextSibling || ancestors(node, root).find(a => a.nextSibling)?.nextSibling;
        }

        // Ensure unique ids on checklists and stars.
        const elementsWithId = [...block.querySelectorAll('[id^=checkId-]')];
        const maxId = Math.max(...[0, ...elementsWithId.map(node => +node.getAttribute('id').substring(8))]);
        let nextId = maxId + 1;
        const ids = [];
        for (const node of block.querySelectorAll('[id^=checkId-], .o_checklist > li, .o_stars')) {
            if (
                !node.classList.contains('o_stars') && (
                    !node.parentElement.classList.contains('o_checklist') ||
                    [...node.children].some(child => ['UL', 'OL'].includes(child.nodeName))
            )) {
                // Remove unique ids from checklists and stars from elements
                // that are no longer checklist items or stars, and from
                // parents of nested lists.
                node.removeAttribute('id')
            } else {
                // Add/change IDs where needed, and ensure they're unique.
                let id = node.getAttribute('id');
                if (!id || ids.includes(id)) {
                    id = `checkId-${nextId}`;
                    nextId++;
                    node.setAttribute('id', id);
                }
                ids.push(id);
            }
        }

        // Update link URL if label is a new valid link.
        const startEl = start && closestElement(start, 'a');
        if (startEl && root.contains(startEl)) {
            const linkLabel = startEl.innerText;
            const urlInfo = getUrlsInfosInString(linkLabel);
            if (urlInfo.length && urlInfo[0].label === linkLabel && !startEl.href.startsWith('mailto:')) {
                startEl.setAttribute('href', urlInfo[0].url);
            }
        }
    }
    return nodeToSanitize;
}
