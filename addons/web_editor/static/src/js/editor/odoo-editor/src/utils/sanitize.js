/** @odoo-module **/
import {
    closestBlock,
    closestElement,
    endPos,
    getListMode,
    isBlock,
    isVisibleEmpty,
    moveNodes,
    preserveCursor,
    isFontAwesome,
    getDeepRange,
    isUnbreakable,
    isEditorTab,
    isZWS,
    isArtificialVoidElement,
    EMAIL_REGEX,
    URL_REGEX_WITH_INFOS,
    unwrapContents,
    padLinkWithZws,
    getTraversedNodes,
    ZERO_WIDTH_CHARS_REGEX,
    setSelection,
    isVisible,
} from './utils.js';

const NOT_A_NUMBER = /[^\d]/g;

function hasPseudoElementContent (node, pseudoSelector) {
    const content = getComputedStyle(node, pseudoSelector).getPropertyValue('content');
    return content && content !== 'none';
}

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
        isNotNoneValue(getComputedStyle(node2, ':after').getPropertyValue('content')) ||
        isFontAwesome(node) || isFontAwesome(node2)
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

/**
 * Returns a URL if link's label is a valid email of http URL, null otherwise.
 *
 * @param {HTMLAnchorElement} link
 * @returns {String|null}
 */
function deduceURLfromLabel(link) {
    // Skip modifying the href for Bootstrap tabs.
    if (link && link.getAttribute("role") === "tab") {
        return;
    }
    const label = link.innerText.trim().replace(ZERO_WIDTH_CHARS_REGEX, '');
    // Check first for e-mail.
    let match = label.match(EMAIL_REGEX);
    if (match) {
        return match[1] ? match[0] : 'mailto:' + match[0];
    }
    // Check for http link.
    // Regex with 'g' flag is stateful, reset lastIndex before and after using
    // exec.
    URL_REGEX_WITH_INFOS.lastIndex = 0;
    match = URL_REGEX_WITH_INFOS.exec(label);
    URL_REGEX_WITH_INFOS.lastIndex = 0;
    if (match && match[0] === label) {
        const currentHttpProtocol = (link.href.match(/^http(s)?:\/\//gi) || [])[0];
        if (match[2]) {
            return match[0];
        } else if (currentHttpProtocol) {
            // Avoid converting a http link to https.
            return currentHttpProtocol + match[0];
        } else {
            return 'https://' + match[0];
        }
    }
    return null;
}

function shouldPreserveCursor(node, root) {
    const selection = root.ownerDocument.getSelection();
    return node.isConnected && selection &&
        selection.anchorNode && root.contains(selection.anchorNode) &&
        selection.focusNode && root.contains(selection.focusNode);
}

class Sanitize {
    constructor(root) {
        this.root = root;
        this.parse(root);
        // Handle unique ids.
        const rootClosestBlock = closestBlock(root);
        if (rootClosestBlock) {
            // Ensure unique ids on checklists and stars.
            const elementsWithId = [...rootClosestBlock.querySelectorAll('[id^=checkId-]')];
            const maxId = Math.max(...[0, ...elementsWithId.map(node => +node.getAttribute('id').substring(8))]);
            let nextId = maxId + 1;
            const ids = [];
            for (const node of rootClosestBlock.querySelectorAll('[id^=checkId-], .o_checklist > li, .o_stars')) {
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
        }
    }

    parse(node) {
        node = closestBlock(node);
        if (node && ['UL', 'OL'].includes(node.tagName)) {
            node = node.parentElement;
        }
        this._parse(node);
    }

    _parse(node) {
        while (node) {
            const closestProtected = closestElement(node, '[data-oe-protected="true"]');
            if (closestProtected && node !== closestProtected) {
                return;
            }
            // Merge identical elements together.
            while (
                areSimilarElements(node, node.previousSibling) &&
                !isUnbreakable(node) &&
                !isEditorTab(node)
            ) {
                getDeepRange(this.root, { select: true });
                const restoreCursor = shouldPreserveCursor(node, this.root) && preserveCursor(this.root.ownerDocument);
                const nodeP = node.previousSibling;
                moveNodes(...endPos(node.previousSibling), node);
                if (restoreCursor) {
                    restoreCursor();
                }
                node = nodeP;
            }

            // Remove comment nodes to avoid issues with mso comments.
            if (node.nodeType === Node.COMMENT_NODE) {
                node.remove();
            }

            const selection = this.root.ownerDocument.getSelection();
            const anchor = selection && selection.anchorNode;
            const anchorEl = anchor && closestElement(anchor);
            // Remove zero-width spaces added by `fillEmpty` when there is
            // content.
            if (
                node.nodeType === Node.TEXT_NODE &&
                node.textContent.includes('\u200B') &&
                node.parentElement.hasAttribute('data-oe-zws-empty-inline') &&
                (
                    node.textContent.length > 1 ||
                    // There can be multiple ajacent text nodes, in which case
                    // the zero-width space is not needed either, despite being
                    // alone (length === 1) in its own text node.
                    Array.from(node.parentNode.childNodes).find(
                        sibling =>
                            sibling !== node &&
                            sibling.nodeType === Node.TEXT_NODE &&
                            sibling.length > 0
                    )
                ) &&
                !isBlock(node.parentElement)
            ) {
                const restoreCursor = shouldPreserveCursor(node, this.root) && preserveCursor(this.root.ownerDocument);
                const shouldAdaptAnchor = anchor === node && selection.anchorOffset > node.textContent.indexOf('\u200B');
                const shouldAdaptFocus = selection.focusNode === node && selection.focusOffset > node.textContent.indexOf('\u200B');
                node.textContent = node.textContent.replace('\u200B', '');
                node.parentElement.removeAttribute("data-oe-zws-empty-inline");
                if (restoreCursor) {
                    restoreCursor();
                }
                if (shouldAdaptAnchor || shouldAdaptFocus) {
                    setSelection(
                        selection.anchorNode, shouldAdaptAnchor ? selection.anchorOffset - 1 : selection.anchorOffset,
                        selection.focusNode, shouldAdaptFocus ? selection.focusOffset - 1 : selection.focusOffset,
                    );
                }
            }

            // Remove empty blocks in <li>
            if (
                node.nodeName === 'P' &&
                node.parentElement.tagName === 'LI' &&
                !node.parentElement.classList.contains('nav-item')
            ) {
                const previous = node.previousSibling;
                const attributes = node.attributes;
                const parent = node.parentElement;
                const restoreCursor = shouldPreserveCursor(node, this.root) && preserveCursor(this.root.ownerDocument);
                if (attributes.length) {
                    const spanEl = document.createElement('span');
                    for (const attribute of attributes) {
                        spanEl.setAttribute(attribute.name, attribute.value);
                    }
                    if (spanEl.style.textAlign) {
                        // This is a tradeoff. Ideally, the state of the html
                        // after this function should be reachable by standard
                        // edition means and a span with display block is not.
                        // However, this is required in order to not break the
                        // design of already existing snippets.
                        spanEl.style.display = 'block';
                    }
                    spanEl.append(...node.childNodes);
                    node.replaceWith(spanEl);
                } else {
                    unwrapContents(node);
                }
                if (previous && isVisible(previous) && !isBlock(previous) && previous.nodeName !== 'BR') {
                    const br = document.createElement('br');
                    previous.after(br);
                }
                if (restoreCursor) {
                    restoreCursor(new Map([[node, parent]]));
                }
                node = parent;
            }

            // Transform <li> into <p> if they are not in a <ul> / <ol>
            if (node.nodeName === 'LI' && !node.closest('ul, ol')) {
                const paragraph = document.createElement("p");
                paragraph.replaceChildren(...node.childNodes);
                node.replaceWith(paragraph);
                node = paragraph;
            }

            // If node is UL or OL and its parent is UL or OL, nest it in an LI
            // with class 'oe-nested'.
            if (
                ['UL', 'OL'].includes(node.nodeName) &&
                ['UL', 'OL'].includes(node.parentNode.nodeName)
            ) {
                const restoreCursor = shouldPreserveCursor(node, this.root) && preserveCursor(this.root.ownerDocument);
                const li = document.createElement('li');
                node.parentNode.insertBefore(li, node);
                li.appendChild(node);
                li.classList.add('oe-nested');
                node = li;
                if (restoreCursor) {
                    restoreCursor();
                }
            }

            // Ensure a zero width space is present inside the FA element.
            if (isFontAwesome(node) && node.textContent !== '\u200B') {
                node.textContent = '\u200B';
            }

            // Ensure the editor tabs align on a 40px grid.
            if (isEditorTab(node)) {
                let tabPreviousSibling = node.previousSibling;
                while (isZWS(tabPreviousSibling)) {
                    tabPreviousSibling = tabPreviousSibling.previousSibling;
                }
                if (isEditorTab(tabPreviousSibling)) {
                    node.style.width = '40px';
                } else {
                    const editable = closestElement(node, '.odoo-editor-editable');
                    if (editable && editable.firstElementChild) {
                        const nodeRect = node.getBoundingClientRect();
                        const referenceRect = editable.firstElementChild.getBoundingClientRect();
                        // Values from getBoundingClientRect() are all zeros
                        // during Editor startup or saving. We cannot
                        // recalculate the tabs width in thoses cases.
                        if (nodeRect.width && referenceRect.width) {
                            const width = (nodeRect.left - referenceRect.left) % 40;
                            node.style.width = (40 - width) + 'px';
                        }
                    }
                }
            }

            // Ensure elements which should not contain any content are tagged
            // contenteditable=false to avoid any hiccup.
            if (
                isArtificialVoidElement(node) &&
                node.getAttribute('contenteditable') !== 'false'
            ) {
                node.setAttribute('contenteditable', 'false');
            }

            // Remove empty class/style attributes.
            for (const attributeName of ['class', 'style']) {
                if (node.nodeType === Node.ELEMENT_NODE && node.hasAttribute(attributeName) && !node.getAttribute(attributeName)) {
                    node.removeAttribute(attributeName);
                }
            }

            let firstChild = node.firstChild;
            // Unwrap the contents of SPAN and FONT elements without attributes.
            if (
                ['SPAN', 'FONT'].includes(node.nodeName)
                && !node.hasAttributes()
                && !hasPseudoElementContent(node, "::before")
                && !hasPseudoElementContent(node, "::after")
            ) {
                getDeepRange(this.root, { select: true });
                const restoreCursor = shouldPreserveCursor(node, this.root) && preserveCursor(this.root.ownerDocument);
                firstChild = unwrapContents(node)[0];
                if (restoreCursor) {
                    restoreCursor();
                }
            }

            if (firstChild) {
                this._parse(firstChild);
            }

            // Remove link ZWNBSP not in selection
            const editable = closestElement(this.root, '[contenteditable=true]');
            if (
                node.nodeType === Node.TEXT_NODE &&
                node.textContent.includes('\uFEFF') &&
                !closestElement(node, 'a') &&
                !(editable && getTraversedNodes(editable).includes(node))
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
                    const newTextNode = document.createTextNode(newText);
                    node.before(newTextNode);
                    node.remove();
                    node = newTextNode;
                }
            }

            // Update link URL if label is a new valid link.
            if (node.nodeName === 'A') {
                if (anchorEl === node) {
                    const url = deduceURLfromLabel(node);
                    if (url) {
                        node.setAttribute('href', url);
                    }
                }
                padLinkWithZws(this.root, node);
            }
            node = node.nextSibling;
        }
    }
}

export function sanitize(root) {
    new Sanitize(root);
    return root;
}
