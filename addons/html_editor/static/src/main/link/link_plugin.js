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

/**
 * @typedef { Object } LinkShared
 * @property { LinkPlugin['createLink'] } createLink
 * @property { LinkPlugin['getPathAsUrlCommand'] } getPathAsUrlCommand
 * @property { LinkPlugin['insertLink'] } insertLink
 */

export class LinkPlugin extends Plugin {
    static id = "link";
    static dependencies = ["dom", "history", "input", "selection", "split", "lineBreak", "overlay"];
    // @phoenix @todo: do we want to have createLink and insertLink methods in link plugin?
    static shared = ["createLink", "insertLink", "getPathAsUrlCommand"];
    resources = {
        user_commands: [
            {
                id: "toggleLinkTools",
                title: _t("Link"),
                description: _t("Add a link"),
                icon: "fa-link",
                run: this.toggleLinkTools.bind(this),
            },
            {
                id: "removeLinkFromSelection",
                title: _t("Remove Link"),
                icon: "fa-unlink",
                isAvailable: isSelectionHasLink,
                run: this.removeLinkFromSelection.bind(this),
            },
        ],

        toolbar_groups: [
            withSequence(40, { id: "link" }),
            withSequence(30, { id: "image_link", namespace: "image" }),
        ],
        toolbar_items: [
            {
                id: "link",
                groupId: "link",
                commandId: "toggleLinkTools",
                isActive: isLinkActive,
            },
            {
                id: "unlink",
                groupId: "link",
                commandId: "removeLinkFromSelection",
            },
            {
                id: "link",
                groupId: "image_link",
                commandId: "toggleLinkTools",
                isActive: isLinkActive,
            },
            {
                id: "unlink",
                groupId: "image_link",
                commandId: "removeLinkFromSelection",
            },
        ],

        powerbox_categories: withSequence(50, { id: "navigation", name: _t("Navigation") }),
        powerbox_items: [
            {
                categoryId: "navigation",
                commandId: "toggleLinkTools",
            },
            {
                title: _t("Button"),
                description: _t("Add a button"),
                categoryId: "navigation",
                commandId: "toggleLinkTools",
            },
        ],

        power_buttons: { commandId: "toggleLinkTools" },

        /** Handlers */
        beforeinput_handlers: withSequence(5, this.onBeforeInput.bind(this)),
        selectionchange_handlers: this.handleSelectionChange.bind(this),
        clean_for_save_handlers: ({ root }) => this.removeEmptyLinks(root),
        normalize_handlers: this.normalizeLink.bind(this),

        /** Overrides */
        split_element_block_overrides: this.handleSplitBlock.bind(this),
        insert_line_break_element_overrides: this.handleInsertLineBreak.bind(this),
    };
    setup() {
        this.overlay = this.dependencies.overlay.createOverlay(LinkPopover, {}, { sequence: 50 });
        this.addDomListener(this.editable, "click", (ev) => {
            if (ev.target.tagName === "A" && ev.target.isContentEditable) {
                if (ev.ctrlKey || ev.metaKey) {
                    window.open(ev.target.href, "_blank");
                }
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
                this.dependencies.selection.focusEditable();
            },
            {
                hotkey: "control+k",
                category: "shortcut_conflict",
                isAvailable: () =>
                    this.dependencies.selection.getSelectionData().documentSelectionIsInEditable,
            }
        );
        this.ignoredClasses = new Set(this.getResource("system_classes"));

        this.getExternalMetaData = memoize(fetchExternalMetaData);
        this.getInternalMetaData = memoize(fetchInternalMetaData);
    }

    destroy() {
        this.removeLinkShortcut();
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
        const selection = this.dependencies.selection.getEditableSelection();
        let link = closestElement(selection.anchorNode, "a");
        if (link) {
            link.setAttribute("href", url);
            link.innerText = label;
        } else {
            link = this.createLink(url, label);
            this.dependencies.dom.insert(link);
        }
        this.dependencies.history.addStep();
        const linkParent = link.parentElement;
        const linkOffset = Array.from(linkParent.childNodes).indexOf(link);
        this.dependencies.selection.setSelection(
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
            title: _t("Paste as URL"),
            description: _t("Create an URL."),
            icon: "fa-link",
            run: () => {
                this.dependencies.dom.insert(this.createLink(url, text));
                this.dependencies.history.addStep();
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
        const { anchorNode } = this.dependencies.selection.getEditableSelection();
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
                this.dependencies.history.addStep();
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
            const selectedNodes = this.dependencies.selection.getSelectedNodes();
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
                        this.dependencies.selection.setCursorEnd(this.linkElement);
                        this.dependencies.selection.focusEditable();
                        this.removeCurrentLinkIfEmtpy();
                        this.dependencies.history.addStep();
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
                        this.dependencies.selection.setSelection(
                            this.dependencies.selection.getEditableSelection()
                        );
                    } else {
                        const restore = prepareUpdate(...leftPos(this.linkElement));
                        this.linkElement.innerText = label;
                        restore();
                        this.overlay.close();
                        this.dependencies.selection.setCursorEnd(this.linkElement);
                    }
                    if (classes) {
                        this.linkElement.className = classes;
                    } else {
                        this.linkElement.removeAttribute("class");
                    }
                    this.dependencies.selection.focusEditable();
                    this.removeCurrentLinkIfEmtpy();
                    this.dependencies.history.addStep();
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
        const selection = this.dependencies.selection.getEditableSelection();
        const linkElement = findInSelection(selection, "a");
        if (linkElement) {
            if (
                !linkElement.contains(selection.anchorNode) ||
                !linkElement.contains(selection.focusNode)
            ) {
                this.dependencies.split.splitSelection();
                const selectedNodes = this.dependencies.selection.getSelectedNodes();
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
                this.dependencies.selection.setCursorEnd(linkElement);
                this.dependencies.history.addStep();
            }
            return linkElement;
        } else {
            // create a new link element
            const selectedNodes = this.dependencies.selection.getSelectedNodes();
            const imageNode = selectedNodes.find((node) => node.tagName === "IMG");

            const link = this.document.createElement("a");
            if (!selection.isCollapsed) {
                const content = this.dependencies.selection.extractContent(selection);
                link.append(content);
                link.normalize();
            }
            this.dependencies.dom.insert(link);
            if (!imageNode) {
                this.dependencies.selection.setCursorEnd(link);
            } else {
                this.dependencies.selection.setSelection({
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
            this.dependencies.history.addStep();
        }
    }

    /**
     * Remove the link from the collapsed selection
     */
    removeLink() {
        const link = this.linkElement;
        const cursors = this.dependencies.selection.preserveSelection();
        if (link && link.isContentEditable) {
            cursors.update(callbacksForCursorUpdate.unwrap(link));
            unwrapContents(link);
        }
        cursors.restore();
        this.linkElement = null;
    }

    removeLinkFromSelection() {
        const selection = this.dependencies.split.splitSelection();
        const cursors = this.dependencies.selection.preserveSelection();

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
        const selectedNodes = this.dependencies.selection.getSelectedNodes();
        const selectedImageNodes = selectedNodes.filter((node) => node.tagName === "IMG");
        if (selectedImageNodes && startLink && endLink && startLink === endLink) {
            for (const imageNode of selectedImageNodes) {
                let imageLink;
                if (direction === DIRECTIONS.RIGHT) {
                    imageLink = this.dependencies.split.splitAroundUntil(imageNode, endLink);
                } else {
                    imageLink = this.dependencies.split.splitAroundUntil(imageNode, startLink);
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
                this.dependencies.history.addStep();
                return;
            }
        }
        if (startLink && startLink.isConnected) {
            anchorNode = this.dependencies.split.splitAroundUntil(anchorNode, startLink);
            anchorOffset = direction === DIRECTIONS.RIGHT ? 0 : nodeSize(anchorNode);
            this.dependencies.selection.setSelection(
                { anchorNode, anchorOffset, focusNode, focusOffset },
                { normalize: true }
            );
        }
        // Only split the end link if it was not already done above.
        if (endLink && endLink.isConnected) {
            focusNode = this.dependencies.split.splitAroundUntil(focusNode, endLink);
            focusOffset = direction === DIRECTIONS.RIGHT ? nodeSize(focusNode) : 0;
            this.dependencies.selection.setSelection(
                { anchorNode, anchorOffset, focusNode, focusOffset },
                { normalize: true }
            );
        }
        const targetedNodes = this.dependencies.selection.getSelectedNodes();
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
        this.dependencies.history.addStep();
    }

    removeEmptyLinks(root) {
        // @todo: check for unremovables
        // @todo: preserve spaces
        for (const link of root.querySelectorAll("a")) {
            if ([...link.childNodes].some(isVisible)) {
                continue;
            }
            const classes = [...link.classList].filter((c) => !this.ignoredClasses.has(c));
            const attributes = [...link.attributes].filter(
                (a) => !["style", "href", "class"].includes(a.name)
            );
            if (!classes.length && !attributes.length) {
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
        let selection = this.dependencies.selection.getEditableSelection();
        if (
            isHtmlContentSupported(selection.anchorNode) &&
            !closestElement(selection.anchorNode, "a") &&
            selection.anchorNode.nodeType === Node.TEXT_NODE
        ) {
            // Merge adjacent text nodes.
            selection.anchorNode.parentNode.normalize();
            selection = this.dependencies.selection.getEditableSelection();
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
                this.dependencies.selection.setCursorStart(nodeForSelectionRestore);
                this.dependencies.history.addStep();
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
        return this.handleEnterAtEdgeOfLink(params, this.dependencies.split.splitElementBlock);
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
        return this.handleEnterAtEdgeOfLink(
            params,
            this.dependencies.lineBreak.insertLineBreakElement
        );
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
