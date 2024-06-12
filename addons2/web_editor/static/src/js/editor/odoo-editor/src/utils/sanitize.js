/** @odoo-module **/
import {
    closestBlock,
    closestElement,
    startPos,
    fillEmpty,
    getListMode,
    isBlock,
    isSelfClosingElement,
    getAdjacentNextSiblings,
    moveNodes,
    preserveCursor,
    isFontAwesome,
    getDeepRange,
    isUnbreakable,
    isEditorTab,
    isProtected,
    isZWS,
    isArtificialVoidElement,
    ancestors,
    EMAIL_REGEX,
    PHONE_REGEX,
    URL_REGEX,
    unwrapContents,
    padLinkWithZws,
    getTraversedNodes,
    ZERO_WIDTH_CHARS_REGEX,
} from './utils.js';

const NOT_A_NUMBER = /[^\d]/g;

// In some cases, we want to prevent merging identical elements.
export const UNMERGEABLE_SELECTORS = [];

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
    if (isFontAwesome(node) || isFontAwesome(node2)) {
        return false;
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
* Returns a complete URL if text is a valid email address, http URL or telephone
* number, null otherwise.
* The optional link parameter is used to prevent protocol switching between
* 'http' and 'https'.
*
* @param {String} text
* @param {HTMLAnchorElement} [link]
* @returns {String|null}
*/
export function deduceURLfromText(text, link) {
   const label = text.replace(ZERO_WIDTH_CHARS_REGEX, '').trim();
   // Check first for e-mail.
   let match = label.match(EMAIL_REGEX);
   if (match) {
       return match[1] ? match[0] : 'mailto:' + match[0];
   }
   // Check for http link.
   match = label.match(URL_REGEX);
   if (match && match[0] === label) {
       const currentHttpProtocol = (link?.href.match(/^http(s)?:\/\//gi) || [])[0];
       if (match[2]) {
           return match[0];
       } else if (currentHttpProtocol) {
           // Avoid converting a http link to https.
           return currentHttpProtocol + match[0];
       } else {
           return 'http://' + match[0];
       }
   }
   // Check for telephone url.
   match = label.match(PHONE_REGEX);
   if (match) {
       return match[1] ? match[0] : 'tel://' + match[0];
   }
   return null;
}

function shouldPreserveCursor(node, root) {
    const selection = root.ownerDocument.getSelection();
    return node.isConnected && selection &&
        selection.anchorNode && root.contains(selection.anchorNode) &&
        selection.focusNode && root.contains(selection.focusNode);
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

    // Remove empty class/style attributes.
    for (const attributeName of ['class', 'style']) {
        if (node.nodeType === Node.ELEMENT_NODE && node.hasAttribute(attributeName) && !node.getAttribute(attributeName)) {
            node.removeAttribute(attributeName);
        }
    }

    if (
        ['SPAN', 'FONT'].includes(node.nodeName)
        && !node.hasAttributes()
        && !hasPseudoElementContent(node, "::before")
        && !hasPseudoElementContent(node, "::after")
    ) {
        // Unwrap the contents of SPAN and FONT elements without attributes.
        getDeepRange(root, { select: true });
        const restoreCursor = shouldPreserveCursor(node, root) && preserveCursor(root.ownerDocument);
        const parent = node.parentElement;
        unwrapContents(node);
        restoreCursor && restoreCursor();
        node = parent; // The node has been removed, update the reference.
    } else if (
        areSimilarElements(node, node.previousSibling) &&
        !isUnbreakable(node) &&
        !isEditorTab(node) &&
        !(
            node.attributes?.length === 1 &&
            node.hasAttribute('data-oe-zws-empty-inline') &&
            (node.textContent === '\u200B' || node.previousSibling.textContent === '\u200B')
        ) &&
        !UNMERGEABLE_SELECTORS.some(selectorClass => node.classList?.contains(selectorClass))
    ) {
        // Merge identical elements together.
        getDeepRange(root, { select: true });
        const restoreCursor = shouldPreserveCursor(node, root) && preserveCursor(root.ownerDocument);
        moveNodes(...startPos(node), node.previousSibling);
        restoreCursor && restoreCursor();
    } else if (node.nodeType === Node.COMMENT_NODE) {
        // Remove comment nodes to avoid issues with mso comments.
        const parent = node.parentElement;
        node.remove();
        node = parent; // The node has been removed, update the reference.
    } else if (
        node.nodeName === 'P' && // Note: not sure we should limit to <p>.
        node.parentElement.nodeName === 'LI' &&
        !node.parentElement.classList.contains('nav-item')
    ) {
        // Remove empty paragraphs in <li>.
        const previous = node.previousSibling;
        const nextSiblings = getAdjacentNextSiblings(node);
        const classes = node.classList;
        const parent = node.parentElement;
        const restoreCursor = shouldPreserveCursor(node, root) && preserveCursor(root.ownerDocument);
        if (previous) {
            const newLi = document.createElement('li');
            newLi.classList.add('oe-nested');
            parent.after(newLi);
            newLi.append(node, ...nextSiblings);
            if (classes.length) {
                const spanEl = document.createElement('span');
                spanEl.setAttribute('class', classes);
                spanEl.append(...node.childNodes);
                node.replaceWith(spanEl);
            } else {
                unwrapContents(node);
            }
        } else {
            if (classes.length) {
                const spanEl = document.createElement('span');
                spanEl.setAttribute('class', classes);
                spanEl.append(...node.childNodes);
                node.replaceWith(spanEl);
            } else {
                unwrapContents(node);
            }
        }
        fillEmpty(parent);
        restoreCursor && restoreCursor(new Map([[node, parent]]));
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
    } else if (node.nodeName === 'A') {
        // Ensure links have ZWNBSPs so the selection can be set at their edges.
        padLinkWithZws(root, node);
    } else if (
        node.nodeType === Node.TEXT_NODE &&
        node.textContent.includes('\uFEFF') &&
        !closestElement(node, 'a') &&
        !(
            closestElement(root, '[contenteditable=true]') &&
            getTraversedNodes(closestElement(root, '[contenteditable=true]')).includes(node)
        )
    ) {
        const startsWithLegitZws = node.textContent.startsWith('\uFEFF') && node.previousSibling && node.previousSibling.nodeName === 'A';
        const endsWithLegitZws = node.textContent.endsWith('\uFEFF') && node.nextSibling && node.nextSibling.nodeName === 'A';
        let newText = node.textContent.replace(/\uFEFF/g, '');
        if (startsWithLegitZws) {
            newText = '\uFEFF' + newText;
        }
        if (endsWithLegitZws) {
            newText = newText + '\uFEFF';
        }
        if (newText !== node.textContent) {
            // We replace the text node with a new text node with the
            // update text rather than just changing the text content of
            // the node because these two methods create different
            // mutations and at least the tour system breaks if all we
            // send here is a text content change.
            let replacement;
            if (newText.length) {
                replacement = document.createTextNode(newText);
                node.before(replacement);
            } else {
                replacement = node.parentElement;
            }
            node.remove();
            node = replacement; // The node has been removed, update the reference.
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
        while (node && !(root.isConnected && !node.isConnected) && root.contains(node)) {
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
            const label = startEl.innerText;
            const url = deduceURLfromText(label, startEl);
            if (url) {
                startEl.setAttribute('href', url);
            }
        }
    }
    return nodeToSanitize;
}
