import { Plugin } from "@html_editor/plugin";
import { unwrapContents } from "@html_editor/utils/dom";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { findInSelection, callbacksForCursorUpdate } from "@html_editor/utils/selection";
import { _t } from "@web/core/l10n/translation";
import { LinkPopover } from "./link_popover";
import { DIRECTIONS, leftPos, nodeSize, rightPos } from "@html_editor/utils/position";
import { prepareUpdate } from "@html_editor/utils/dom_state";
import { EMAIL_REGEX, URL_REGEX, cleanZWChars, deduceURLfromText } from "./utils";
import { isVisible } from "@html_editor/utils/dom_info";
import { KeepLast } from "@web/core/utils/concurrency";
import { rpc } from "@web/core/network/rpc";
import { memoize } from "@web/core/utils/functions";
import { withSequence } from "@html_editor/utils/resource";

/**
 * @typedef {import("@html_editor/core/selection_plugin").EditorSelection} EditorSelection
 */

/**
 * @param {EditorSelection} selection
 */
function isLinkActive(selection) {
    const linkElementAnchor = closestElement(selection.anchorNode, "A");
    const linkElementFocus = closestElement(selection.focusNode, "A");
    if (linkElementFocus && linkElementAnchor) {
        return linkElementAnchor === linkElementFocus;
    }
    if (linkElementAnchor || linkElementFocus) {
        return true;
    }

    return false;
}

function isSelectionHasLink(selection) {
    return findInSelection(selection, "a") ? true : false;
}

/**
 * @param { HTMLAnchorElement } link
 * @param {number} offset
 * @returns {"start"|"end"|false}
 */
function isPositionAtEdgeofLink(link, offset) {
    const childNodes = [...link.childNodes];
    let firstVisibleIndex = childNodes.findIndex(isVisible);
    firstVisibleIndex = firstVisibleIndex === -1 ? 0 : firstVisibleIndex;
    if (offset <= firstVisibleIndex) {
        return "start";
    }
    let lastVisibleIndex = childNodes.reverse().findIndex(isVisible);
    lastVisibleIndex = lastVisibleIndex === -1 ? 0 : childNodes.length - lastVisibleIndex;
    if (offset >= lastVisibleIndex) {
        return "end";
    }
    return false;
}

async function fetchExternalMetaData(url) {
    // Get the external metadata
    try {
        return await rpc("/html_editor/link_preview_external", {
            preview_url: url,
        });
    } catch {
        // when it's not possible to fetch the metadata we don't want to block the ui
        return;
    }
}

async function fetchInternalMetaData(url) {
    // Get the internal metadata
    const keepLastPromise = new KeepLast();
    const urlParsed = new URL(url);

    const result = await keepLastPromise
        .add(fetch(urlParsed))
        .then((response) => response.text())
        .then(async (content) => {
            const html_parser = new window.DOMParser();
            const doc = html_parser.parseFromString(content, "text/html");
            const internalUrlMetaData = await rpc("/html_editor/link_preview_internal", {
                preview_url: urlParsed.pathname,
            });

            internalUrlMetaData["favicon"] = doc.querySelector("link[rel~='icon']");
            internalUrlMetaData["ogTitle"] = doc.querySelector("[property='og:title']");
            internalUrlMetaData["title"] = doc.querySelector("title");

            return internalUrlMetaData;
        })
        .catch((error) => {
            // HTTP error codes should not prevent to edit the links, so we
            // only check for proper instances of Error.
            if (error instanceof Error) {
                return Promise.reject(error);
            }
        });
    return result;
}

const linkItem = {
    id: "link",
    title: _t("Link"),
    action(dispatch) {
        dispatch("CREATE_LINK_ON_SELECTION");
    },
    icon: "fa-link",
    isFormatApplied: isLinkActive,
};
const unlinkItem = {
    id: "unlink",
    title: _t("Remove Link"),

    action(dispatch) {
        dispatch("REMOVE_LINK_FROM_SELECTION");
    },
    icon: "fa-unlink",
    isAvailable: isSelectionHasLink,
};

export class LinkPlugin extends Plugin {
    static name = "link";
    static dependencies = ["dom", "selection", "split", "line_break", "overlay"];
    // @phoenix @todo: do we want to have createLink and insertLink methods in link plugin?
    static shared = ["createLink", "insertLink", "getPathAsUrlCommand"];
    resources = {
        onBeforeInput: withSequence(5, this.onBeforeInput.bind(this)),
        toolbarCategory: [
            withSequence(40, {
                id: "link",
            }),
            withSequence(30, {
                id: "image_link",
                namespace: "image",
            }),
        ],
        toolbarItems: [
            {
                ...linkItem,
                category: "link",
            },
            {
                ...unlinkItem,
                category: "link",
            },
            {
                ...linkItem,
                category: "image_link",
            },
            {
                ...unlinkItem,
                category: "image_link",
            },
        ],

        powerboxCategory: withSequence(50, { id: "navigation", name: _t("Navigation") }),
        powerboxItems: [
            {
                id: "link",
                name: _t("Link"),
                description: _t("Add a link"),
                category: "navigation",
                fontawesome: "fa-link",
                action(dispatch) {
                    dispatch("TOGGLE_LINK");
                },
            },
            {
                name: _t("Button"),
                description: _t("Add a button"),
                category: "navigation",
                fontawesome: "fa-link",
                action(dispatch) {
                    dispatch("TOGGLE_LINK");
                },
            },
        ],
        onSelectionChange: this.handleSelectionChange.bind(this),
        split_element_block: this.handleSplitBlock.bind(this),
        handle_insert_line_break_element: this.handleInsertLineBreak.bind(this),
        powerButtons: ["link"],
    };
    setup() {
        this.overlay = this.shared.createOverlay(LinkPopover, {}, { sequence: 40 });
        this.addDomListener(this.editable, "click", (ev) => {
            if (ev.target.tagName === "A" && ev.target.isContentEditable) {
                ev.preventDefault();
                this.toggleLinkTools({ link: ev.target });
            }
        });
        // link creation is added to the command service because of a shortcut conflict,
        // as ctrl+k is used for invoking the command palette
        this.removeLinkShortcut = this.services.command.add(
            "Create link",
            () => {
                this.toggleLinkTools();
                this.shared.focusEditable();
            },
            {
                hotkey: "control+k",
                category: "shortcut_conflict",
                isAvailable: () => this.shared.getSelectionData().documentSelectionIsInEditable,
            }
        );
        this.ignoredClasses = new Set(this.getResource("link_ignore_classes"));

        this.getExternalMetaData = memoize(fetchExternalMetaData);
        this.getInternalMetaData = memoize(fetchInternalMetaData);
    }

    destroy() {
        this.removeLinkShortcut();
    }

    handleCommand(command, payload) {
        switch (command) {
            case "CREATE_LINK_ON_SELECTION":
                this.toggleLinkTools(payload.options);
                break;
            case "TOGGLE_LINK":
                this.toggleLinkTools(payload.options);
                break;
            case "NORMALIZE":
                this.normalizeLink();
                break;
            case "CLEAN_FOR_SAVE":
                this.removeEmptyLinks(payload.root);
                break;
            case "REMOVE_LINK_FROM_SELECTION":
                this.removeLinkFromSelection();
                break;
        }
    }

    // -------------------------------------------------------------------------
    // Commands
    // -------------------------------------------------------------------------

    /**
     * @param {string} url
     * @param {string} label
     */
    createLink(url, label) {
        const link = this.document.createElement("a");
        link.setAttribute("href", url);
        for (const [param, value] of Object.entries(this.config.defaultLinkAttributes || {})) {
            link.setAttribute(param, `${value}`);
        }
        link.innerText = label;
        return link;
    }
    /**
     * @param {string} url
     * @param {string} label
     */
    insertLink(url, label) {
        const selection = this.shared.getEditableSelection();
        let link = closestElement(selection.anchorNode, "a");
        if (link) {
            link.setAttribute("href", url);
            link.innerText = label;
        } else {
            link = this.createLink(url, label);
            this.shared.domInsert(link);
        }
        this.dispatch("ADD_STEP");
        const linkParent = link.parentElement;
        const linkOffset = Array.from(linkParent.childNodes).indexOf(link);
        this.shared.setSelection(
            { anchorNode: linkParent, anchorOffset: linkOffset + 1 },
            { normalize: false }
        );
    }
    /**
     * @param {string} text
     * @param {string} url
     */
    getPathAsUrlCommand(text, url) {
        const pasteAsURLCommand = {
            name: _t("Paste as URL"),
            description: _t("Create an URL."),
            fontawesome: "fa-link",
            action: () => {
                this.shared.domInsert(this.createLink(url, text));
                this.dispatch("ADD_STEP");
            },
        };
        return pasteAsURLCommand;
    }
    /**
     * Toggle the Link popover to edit links
     *
     * @param {Object} options
     * @param {HTMLElement} options.link
     */
    toggleLinkTools({ link } = {}) {
        if (!link) {
            link = this.getOrCreateLink();
        }
        this.linkElement = link;
    }

    normalizeLink() {
        const { anchorNode } = this.shared.getEditableSelection();
        const linkEl = closestElement(anchorNode, "a");
        if (linkEl && linkEl.isContentEditable) {
            const label = linkEl.innerText;
            const url = deduceURLfromText(label, linkEl);
            if (url) {
                linkEl.setAttribute("href", url);
            }
        }
    }

    handleSelectionChange(selectionData) {
        const selection = selectionData.editableSelection;
        const props = {
            onRemove: () => {
                this.removeLink();
                this.overlay.close();
                this.dispatch("ADD_STEP");
            },
            onCopy: () => {
                this.overlay.close();
            },
            onClose: () => {
                this.overlay.close();
            },
            getInternalMetaData: this.getInternalMetaData,
            getExternalMetaData: this.getExternalMetaData,
        };
        if (!selectionData.documentSelectionIsInEditable) {
            // note that data-prevent-closing-overlay also used in color picker but link popover
            // and color picker don't open at the same time so it's ok to query like this
            const popoverEl = document.querySelector("[data-prevent-closing-overlay=true]");
            if (popoverEl?.contains(selectionData.documentSelection.anchorNode)) {
                return;
            }
            this.overlay.close();
        } else if (!selection.isCollapsed) {
            const selectedNodes = this.shared.getSelectedNodes();
            const imageNode = selectedNodes.find((node) => node.tagName === "IMG");
            if (imageNode && imageNode.parentNode.tagName === "A") {
                if (this.linkElement !== imageNode.parentElement) {
                    this.overlay.close();
                    this.removeCurrentLinkIfEmtpy();
                }
                this.linkElement = imageNode.parentElement;

                const imageLinkProps = {
                    ...props,
                    isImage: true,
                    linkEl: this.linkElement,
                    onApply: (url, _) => {
                        this.linkElement.href = url;
                        this.shared.setCursorEnd(this.linkElement);
                        this.shared.focusEditable();
                        this.removeCurrentLinkIfEmtpy();
                        this.dispatch("ADD_STEP");
                    },
                };

                // close the overlay to always position the popover to the bottom of selected image
                if (this.overlay.isOpen) {
                    this.overlay.close();
                }
                this.overlay.open({ target: imageNode, props: imageLinkProps });
            } else {
                this.overlay.close();
            }
        } else {
            const linkEl = closestElement(selection.anchorNode, "A");
            if (!linkEl) {
                this.overlay.close();
                this.removeCurrentLinkIfEmtpy();
                return;
            }
            if (linkEl !== this.linkElement) {
                this.removeCurrentLinkIfEmtpy();
                this.overlay.close();
                this.linkElement = linkEl;
            }

            // if the link includes an inline image, we close the previous opened popover to reposition it
            const imageNode = linkEl.querySelector("img");
            if (imageNode) {
                this.removeCurrentLinkIfEmtpy();
                this.overlay.close();
            }

            const linkProps = {
                ...props,
                isImage: false,
                linkEl: this.linkElement,
                onApply: (url, label, classes) => {
                    this.linkElement.href = url;
                    if (cleanZWChars(this.linkElement.innerText) === label) {
                        this.overlay.close();
                        this.shared.setSelection(this.shared.getEditableSelection());
                    } else {
                        const restore = prepareUpdate(...leftPos(this.linkElement));
                        this.linkElement.innerText = label;
                        restore();
                        this.overlay.close();
                        this.shared.setCursorEnd(this.linkElement);
                    }
                    if (classes) {
                        this.linkElement.className = classes;
                    } else {
                        this.linkElement.removeAttribute("class");
                    }
                    this.shared.focusEditable();
                    this.removeCurrentLinkIfEmtpy();
                    this.dispatch("ADD_STEP");
                },
            };

            if (linkEl.isConnected) {
                // pass the link element to overlay to prevent position change
                this.overlay.open({ target: this.linkElement, props: linkProps });
            }
        }
    }

    /**
     * get the link from the selection or create one if there is none
     *
     * @return {HTMLElement}
     */
    getOrCreateLink() {
        const selection = this.shared.getEditableSelection();
        const linkElement = findInSelection(selection, "a");
        if (linkElement) {
            if (
                !linkElement.contains(selection.anchorNode) ||
                !linkElement.contains(selection.focusNode)
            ) {
                this.shared.splitSelection();
                const selectedNodes = this.shared.getSelectedNodes();
                let before = linkElement.previousSibling;
                while (before !== null && selectedNodes.includes(before)) {
                    linkElement.insertBefore(before, linkElement.firstChild);
                    before = linkElement.previousSibling;
                }
                let after = linkElement.nextSibling;
                while (after !== null && selectedNodes.includes(after)) {
                    linkElement.appendChild(after);
                    after = linkElement.nextSibling;
                }
                this.shared.setCursorEnd(linkElement);
                this.dispatch("ADD_STEP");
            }
            return linkElement;
        } else {
            // create a new link element
            const selectedNodes = this.shared.getSelectedNodes();
            const imageNode = selectedNodes.find((node) => node.tagName === "IMG");

            const link = this.document.createElement("a");
            if (!selection.isCollapsed) {
                const content = this.shared.extractContent(selection);
                link.append(content);
                link.normalize();
            }
            this.shared.domInsert(link);
            if (!imageNode) {
                this.shared.setCursorEnd(link);
            } else {
                this.shared.setSelection({
                    anchorNode: link,
                    anchorOffset: 0,
                    focusNode: link,
                    focusOffset: nodeSize(link),
                });
            }
            return link;
        }
    }

    removeCurrentLinkIfEmtpy() {
        if (
            this.linkElement &&
            cleanZWChars(this.linkElement.innerText) === "" &&
            !this.linkElement.querySelector("img")
        ) {
            this.linkElement.remove();
        }
        if (
            this.linkElement &&
            !this.linkElement.href &&
            !this.linkElement.hasAttribute("t-attf-href") &&
            !this.linkElement.hasAttribute("t-att-href")
        ) {
            this.removeLink();
            this.dispatch("ADD_STEP");
        }
    }

    /**
     * Remove the link from the collapsed selection
     */
    removeLink() {
        const link = this.linkElement;
        const cursors = this.shared.preserveSelection();
        if (link && link.isContentEditable) {
            cursors.update(callbacksForCursorUpdate.unwrap(link));
            unwrapContents(link);
        }
        cursors.restore();
        this.linkElement = null;
    }

    removeLinkFromSelection() {
        const selection = this.shared.splitSelection();
        const cursors = this.shared.preserveSelection();

        // If not, unlink only the part(s) of the link(s) that are selected:
        // `<a>a[b</a>c<a>d</a>e<a>f]g</a>` => `<a>a</a>[bcdef]<a>g</a>`.
        let { anchorNode, focusNode, anchorOffset, focusOffset } = selection;
        const direction = selection.direction;
        // Split the links around the selection.
        let [startLink, endLink] = [
            closestElement(anchorNode, "a"),
            closestElement(focusNode, "a"),
        ];
        // to remove link from selected images
        const selectedNodes = this.shared.getSelectedNodes();
        const selectedImageNodes = selectedNodes.filter((node) => node.tagName === "IMG");
        if (selectedImageNodes && startLink && endLink && startLink === endLink) {
            for (const imageNode of selectedImageNodes) {
                let imageLink;
                if (direction === DIRECTIONS.RIGHT) {
                    imageLink = this.shared.splitAroundUntil(imageNode, endLink);
                } else {
                    imageLink = this.shared.splitAroundUntil(imageNode, startLink);
                }
                cursors.update(callbacksForCursorUpdate.unwrap(imageLink));
                unwrapContents(imageLink);
                // update the links at the selection
                [startLink, endLink] = [
                    closestElement(anchorNode, "a"),
                    closestElement(focusNode, "a"),
                ];
            }
            cursors.restore();
            // when only unlink an inline image, add step after the unwrapping
            if (
                selectedImageNodes.length === 1 &&
                selectedImageNodes.length === selectedNodes.length
            ) {
                this.dispatch("ADD_STEP");
                return;
            }
        }
        if (startLink && startLink.isConnected) {
            anchorNode = this.shared.splitAroundUntil(anchorNode, startLink);
            anchorOffset = direction === DIRECTIONS.RIGHT ? 0 : nodeSize(anchorNode);
            this.shared.setSelection(
                { anchorNode, anchorOffset, focusNode, focusOffset },
                { normalize: true }
            );
        }
        // Only split the end link if it was not already done above.
        if (endLink && endLink.isConnected) {
            focusNode = this.shared.splitAroundUntil(focusNode, endLink);
            focusOffset = direction === DIRECTIONS.RIGHT ? nodeSize(focusNode) : 0;
            this.shared.setSelection(
                { anchorNode, anchorOffset, focusNode, focusOffset },
                { normalize: true }
            );
        }
        const targetedNodes = this.shared.getSelectedNodes();
        const links = new Set(
            targetedNodes
                .map((node) => closestElement(node, "a"))
                .filter((a) => a && a.isContentEditable)
        );
        if (links.size) {
            for (const link of links) {
                cursors.update(callbacksForCursorUpdate.unwrap(link));
                unwrapContents(link);
            }
            cursors.restore();
        }
        this.dispatch("ADD_STEP");
    }

    removeEmptyLinks(root) {
        // @todo: check for unremovables
        // @todo: preserve spaces
        for (const link of root.querySelectorAll("a")) {
            if ([...link.childNodes].some(isVisible)) {
                continue;
            }
            const classes = [...link.classList].filter((c) => !this.ignoredClasses.has(c));
            if (!classes.length) {
                link.remove();
            }
        }
    }

    onBeforeInput(ev) {
        if (
            ev.inputType === "insertParagraph" ||
            ev.inputType === "insertLineBreak" ||
            (ev.inputType === "insertText" && ev.data === " ")
        ) {
            this.handleAutomaticLinkInsertion();
        }
    }
    /**
     * Inserts a link in the editor. Called after pressing space or (shif +) enter.
     * Performs a regex check to determine if the url has correct syntax.
     */
    handleAutomaticLinkInsertion() {
        let selection = this.shared.getEditableSelection();
        if (
            isHtmlContentSupported(selection.anchorNode) &&
            !closestElement(selection.anchorNode, "a") &&
            selection.anchorNode.nodeType === Node.TEXT_NODE
        ) {
            // Merge adjacent text nodes.
            selection.anchorNode.parentNode.normalize();
            selection = this.shared.getEditableSelection();
            const textSliced = selection.anchorNode.textContent.slice(0, selection.anchorOffset);
            const textNodeSplitted = textSliced.split(/\s/);
            const potentialUrl = textNodeSplitted.pop();
            // In case of multiple matches, only the last one will be converted.
            const match = [...potentialUrl.matchAll(new RegExp(URL_REGEX, "g"))].pop();

            if (match && !EMAIL_REGEX.test(match[0])) {
                const nodeForSelectionRestore = selection.anchorNode.splitText(
                    selection.anchorOffset
                );
                const url = match[2] ? match[0] : "http://" + match[0];
                const startOffset = selection.anchorOffset - potentialUrl.length + match.index;
                const text = selection.anchorNode.textContent.slice(
                    startOffset,
                    startOffset + match[0].length
                );
                const link = this.createLink(url, text);
                // split the text node and replace the url text with the link
                const textNodeToReplace = selection.anchorNode.splitText(startOffset);
                textNodeToReplace.splitText(match[0].length);
                selection.anchorNode.parentElement.replaceChild(link, textNodeToReplace);
                this.shared.setCursorStart(nodeForSelectionRestore);
                this.dispatch("ADD_STEP");
            }
        }
    }

    /**
     * Special behavior for links: do not break the link at its edges, but
     * rather before/after it.
     *
     * @param {Object} params
     * @param {Element} params.targetNode
     * @param {number} params.targetOffset
     * @param {Element} params.blockToSplit
     */
    handleSplitBlock(params) {
        return this.handleEnterAtEdgeOfLink(params, this.shared.splitElementBlock);
    }

    /**
     * Special behavior for links: do not add a line break at its edges, but
     * rather outside it.
     *
     * @param {Object} params
     * @param {Element} params.targetNode
     * @param {number} params.targetOffset
     */
    handleInsertLineBreak(params) {
        return this.handleEnterAtEdgeOfLink(params, this.shared.insertLineBreakElement);
    }

    /**
     * @param {Object} params
     * @param {Element} params.targetNode
     * @param {number} params.targetOffset
     * @param {Element} [params.blockToSplit]
     * @param {Function} splitOrLineBreakCallback
     */
    handleEnterAtEdgeOfLink(params, splitOrLineBreakCallback) {
        // @todo: handle target Node being a descendent of a link (iterate over
        // leaves inside the link, rather than childNodes)
        let { targetNode, targetOffset } = params;
        if (targetNode.tagName !== "A") {
            return;
        }
        const edge = isPositionAtEdgeofLink(targetNode, targetOffset);
        if (!edge) {
            return;
        }
        [targetNode, targetOffset] = edge === "start" ? leftPos(targetNode) : rightPos(targetNode);
        splitOrLineBreakCallback({ ...params, targetNode, targetOffset });
        return true;
    }
}

// @phoenix @todo: duplicate from the clipboard plugin, should be moved to a shared location
/**
 * Returns true if the provided node can suport html content.
 *
 * @param {Node} node
 * @returns {boolean}
 */
export function isHtmlContentSupported(node) {
    return !closestElement(
        node,
        '[data-oe-model]:not([data-oe-field="arch"]):not([data-oe-type="html"]),[data-oe-translation-id]',
        true
    );
}
