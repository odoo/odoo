import { Plugin } from "@html_editor/plugin";
import { unwrapContents } from "@html_editor/utils/dom";
import { closestElement, selectElements } from "@html_editor/utils/dom_traversal";
import { findInSelection, callbacksForCursorUpdate } from "@html_editor/utils/selection";
import { _t } from "@web/core/l10n/translation";
import { LinkPopover } from "./link_popover";
import { DIRECTIONS, leftPos, nodeSize, rightPos } from "@html_editor/utils/position";
import { EMAIL_REGEX, URL_REGEX, cleanZWChars, deduceURLfromText } from "./utils";
import { isVisible } from "@html_editor/utils/dom_info";
import { KeepLast } from "@web/core/utils/concurrency";
import { rpc } from "@web/core/network/rpc";
import { memoize } from "@web/core/utils/functions";
import { withSequence } from "@html_editor/utils/resource";
import { isBlock } from "@html_editor/utils/blocks";

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

/**
 * @param {EditorSelection} selection
 */
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

async function fetchAttachmentMetaData(url, ormService) {
    try {
        const urlParsed = new URL(url, window.location.origin);
        const attachementId = parseInt(urlParsed.pathname.split("/").pop());
        const [{ name, mimetype }] = await ormService.read(
            "ir.attachment",
            [attachementId],
            ["name", "mimetype"]
        );
        return { name, mimetype };
    } catch {
        return { name: url, mimetype: undefined };
    }
}

/**
 * @typedef { Object } LinkShared
 * @property { LinkPlugin['createLink'] } createLink
 * @property { LinkPlugin['getPathAsUrlCommand'] } getPathAsUrlCommand
 * @property { LinkPlugin['insertLink'] } insertLink
 */

export class LinkPlugin extends Plugin {
    static id = "link";
    static dependencies = [
        "dom",
        "history",
        "input",
        "selection",
        "split",
        "lineBreak",
        "overlay",
        "color",
    ];
    // @phoenix @todo: do we want to have createLink and insertLink methods in link plugin?
    static shared = ["createLink", "insertLink", "getPathAsUrlCommand"];
    resources = {
        user_commands: [
            {
                id: "openLinkTools",
                title: _t("Link"),
                description: _t("Add a link"),
                icon: "fa-link",
                run: ({ link, type} = {}) => this.openLinkTools(link, type),
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
                commandId: "openLinkTools",
                isActive: isLinkActive,
                isDisabled: () => !this.isLinkAllowedOnSelection(),
            },
            {
                id: "unlink",
                groupId: "link",
                commandId: "removeLinkFromSelection",
            },
            {
                id: "link",
                groupId: "image_link",
                commandId: "openLinkTools",
                isActive: isLinkActive,
                isDisabled: () => !this.isLinkAllowedOnSelection(),
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
                commandId: "openLinkTools",
            },
            {
                title: _t("Button"),
                description: _t("Add a button"),
                categoryId: "navigation",
                commandId: "openLinkTools",
                commandParams: { type: "primary" },
            },
        ],

        power_buttons: { commandId: "openLinkTools" },

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
        this.overlay = this.dependencies.overlay.createOverlay(
            LinkPopover,
            {
                closeOnPointerdown: false,
            },
            { sequence: 50 }
        );
        this.addDomListener(this.editable, "click", (ev) => {
            if (ev.target.tagName === "A" && ev.target.isContentEditable) {
                if (ev.ctrlKey || ev.metaKey) {
                    window.open(ev.target.href, "_blank");
                }
                ev.preventDefault();
            }
        });
        // link creation is added to the command service because of a shortcut conflict,
        // as ctrl+k is used for invoking the command palette
        this.unregisterLinkCommandCallback = this.services.command.add(
            "Create link",
            () => {
                this.dependencies.selection.focusEditable();
                // To avoid a race condition between the events spawn by :
                // 1. the `focus editable` and
                // 2. the odoo `Shortcut bar` closure
                // Which can affect the link overlay opening sequence if we keep it in sync.
                // Therefore we need to wait for the next tick before triggering openLinkTools.
                setTimeout(() => this.openLinkTools());
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
        this.getAttachmentMetadata = memoize((url) =>
            fetchAttachmentMetaData(url, this.services.orm)
        );
    }

    destroy() {
        this.unregisterLinkCommandCallback();
    }

    // -------------------------------------------------------------------------
    // Commands
    // -------------------------------------------------------------------------

    /**
     * @param {string} url
     * @param {string} label
     *
     * @return {HTMLElement} link
     */
    createLink(url, label = "") {
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

    isLinkAllowedOnSelection() {
        const linksInSelection = this.dependencies.selection
            .getTraversedNodes()
            .filter((n) => n.tagName === "A");
        return (
            linksInSelection.length < 2 && this.dependencies.selection.getTraversedBlocks().size < 2
        );
    }

    /**
     * open the Link popover to edit links
     *
     * @param {HTMLElement} [linkElement]
     */
    openLinkTools(linkElement, type) {
        this.closeLinkTools();
        if (!this.isLinkAllowedOnSelection()) {
            return this.services.notification.add(
                _t("Unable to create a link on the current selection."),
                { type: "danger" }
            );
        }
        let selection = this.dependencies.selection.getEditableSelection();
        let cursorsToRestore = this.dependencies.selection.preserveSelection();
        const commonAncestor = closestElement(selection.commonAncestorContainer);
        linkElement = linkElement || findInSelection(selection, "a");
        this.type = type;
        if (
            linkElement &&
            (!linkElement.contains(selection.anchorNode) ||
                !linkElement.contains(selection.focusNode))
        ) {
            this.extendLinkToSelection(linkElement, selection);
            linkElement = findInSelection(selection, "a");
            this.dependencies.history.addStep();
            cursorsToRestore = this.dependencies.selection.preserveSelection();
        }
        this.linkInDocument = linkElement;
        if (!linkElement) {
            // create a new link element
            linkElement = this.document.createElement("a");
            if (!selection.isCollapsed) {
                linkElement.append(selection.textContent());
            }
        }

        const selectionTextContent = selection?.textContent();
        const isImage = !!findInSelection(selection, "img");

        const applyCallback = (url, label, classes) => {
            if (this.linkInDocument && isImage) {
                if (url) {
                    this.linkInDocument.href = url;
                } else {
                    this.linkInDocument.removeAttribute("href");
                }
            } else if (this.linkInDocument) {
                if (url) {
                    this.linkInDocument.href = url;
                } else {
                    this.linkInDocument.removeAttribute("href");
                }
                if (classes) {
                    this.linkInDocument.className = classes;
                } else {
                    this.linkInDocument.removeAttribute("class");
                }
                if (cleanZWChars(this.linkInDocument.innerText) !== label) {
                    this.linkInDocument.innerText = label;
                    cursorsToRestore = null;
                }
            } else if (url) {
                // prevent the link creation if the url field was empty

                // create a new link with current selection as a content
                if ((selectionTextContent && selectionTextContent === label) || isImage) {
                    const link = this.createLink(url);
                    const content = this.dependencies.selection.extractContent(selection);
                    link.append(content);
                    if (classes) {
                        link.className = classes;
                    }
                    link.normalize();
                    this.linkInDocument = link;
                    cursorsToRestore = null;
                    selection = this.dependencies.selection.getEditableSelection();
                    const anchorClosestElement = closestElement(selection.anchorNode);
                    if (commonAncestor !== anchorClosestElement) {
                        // We force the cursor after the anchorClosestElement
                        // To be sure the link is inserted in the correct place in the dom.
                        const [anchorNode, anchorOffset] = rightPos(anchorClosestElement);
                        this.dependencies.selection.setSelection(
                            { anchorNode, anchorOffset },
                            { normalize: false }
                        );
                    }
                    this.dependencies.dom.insert(link);
                } else if (label) {
                    const link = this.createLink(url, label);
                    if (classes) {
                        link.className = classes;
                    }
                    this.linkInDocument = link;
                    cursorsToRestore = null;
                    this.dependencies.dom.insert(link);
                }
            }
            this.closeLinkTools(cursorsToRestore);
            this.dependencies.selection.focusEditable();
            this.dependencies.history.addStep();
        };

        const props = {
            linkElement,
            isImage: isImage,
            onApply: applyCallback,
            onRemove: () => {
                this.removeLinkInDocument();
                this.linkInDocument = null;
                this.overlay.close();
            },
            onCopy: () => {
                this.linkInDocument = null;
                this.overlay.close();
            },
            onClose: () => {
                this.linkInDocument = null;
                this.overlay.close();
            },
            getInternalMetaData: this.getInternalMetaData,
            getExternalMetaData: this.getExternalMetaData,
            getAttachmentMetadata: this.getAttachmentMetadata,
            recordInfo: this.config.getRecordInfo?.() || {},
            canEdit:
                !this.linkInDocument || !this.linkInDocument.classList.contains("o_link_readonly"),
            canUpload: !this.config.disableFile,
            onUpload: this.config.onAttachmentChange,
            type: this.type || "",
        };
        this.overlay.open({ props });
    }
    /**
     * close the link tool
     *
     */
    closeLinkTools(cursors = null) {
        const link = this.linkInDocument;
        this.linkInDocument = null;
        // Some unit tests fail when this.overlay.isOpen but the DOM don't contain the linkPopover yet.
        // Because of some kind of race condition between the hoot mock event and the owl renderer.
        // This is why we check for the popover in the DOM.
        if (this.overlay.isOpen && document.querySelector(".o-we-linkpopover")) {
            this.overlay.close();
            if (link && link.isConnected) {
                this.dependencies.selection.setSelection({
                    anchorNode: link,
                    anchorOffset: 0,
                    focusNode: link,
                    focusOffset: nodeSize(link),
                });
                this.dependencies.color.removeAllColor();
                // Remove the current link (linkInDocument) if it has no content
                if (cleanZWChars(link.innerText) === "" && !link.querySelector("img")) {
                    const [anchorNode, anchorOffset] = rightPos(link);
                    // We force the cursor after the link before removing the link
                    // to ensure we don't lose the selection position.
                    this.dependencies.selection.setSelection(
                        { anchorNode, anchorOffset },
                        { normalize: false }
                    );
                    link.remove();
                } else if (cursors) {
                    cursors.restore();
                } else {
                    this.dependencies.selection.setCursorEnd(link);
                }
            }
        }
    }

    normalizeLink(root) {
        const { anchorNode } = this.dependencies.selection.getEditableSelection();
        const linkEl = closestElement(anchorNode, "a");
        if (linkEl && linkEl.isContentEditable) {
            const label = linkEl.innerText;
            const url = deduceURLfromText(label, linkEl);
            if (url) {
                linkEl.setAttribute("href", url);
            }
        }
        for (const anchorEl of selectElements(root, "a")) {
            const { color } = anchorEl.style;
            const childNodes = [...anchorEl.childNodes];
            // For each anchor element, if it has an inline color style,
            // (converted from an external style), remove it from the anchor,
            // create a font tag inside it, and move the color to the font tag.
            // This ensures the color is applied to the font element instead of
            // the anchor element itself.
            if (color && childNodes.every((n) => !isBlock(n))) {
                anchorEl.style.removeProperty("color");
                const font = selectElements(anchorEl, "font").next().value;
                if (font && anchorEl.textContent === font.textContent) {
                    continue;
                }
                const newFont = this.document.createElement("font");
                newFont.append(...childNodes);
                anchorEl.appendChild(newFont);
                this.dependencies.color.colorElement(newFont, color, "color");
            }
        }
    }

    handleSelectionChange(selectionData) {
        const selection = selectionData.editableSelection;
        if (!selectionData.documentSelectionIsInEditable) {
            // note that data-prevent-closing-overlay also used in color picker but link popover
            // and color picker don't open at the same time so it's ok to query like this
            const popoverEl = document.querySelector("[data-prevent-closing-overlay=true]");
            if (popoverEl?.contains(selectionData.documentSelection.anchorNode)) {
                return;
            }
            this.linkInDocument = null;
            this.closeLinkTools();
        } else if (!selection.isCollapsed) {
            // Open the link tool only if we have an image selected
            const imageNode = findInSelection(selection, "img");
            if (imageNode?.parentNode?.tagName === "A" && this.isLinkAllowedOnSelection()) {
                this.openLinkTools(imageNode.parentElement);
            } else {
                this.linkInDocument = null;
                this.closeLinkTools();
            }
        } else {
            const closestLinkElement = closestElement(selection.anchorNode, "A");
            if (closestLinkElement) {
                if (closestLinkElement !== this.linkInDocument) {
                    this.openLinkTools(closestLinkElement);
                }
            } else {
                this.linkInDocument = null;
                this.closeLinkTools();
            }
        }
    }

    /**
     * extend the given link element to include all content from the given selection
     *
     * @param {HTMLLinkElement} linkElement
     * @param {EditorSelection} selection
     * @return {boolean}
     */
    extendLinkToSelection(linkElement, selection) {
        this.dependencies.split.splitSelection();
        const selectedNodes = this.dependencies.selection.getSelectedNodes();
        let before = linkElement.previousSibling;
        while (before !== null && selectedNodes.includes(before)) {
            linkElement.insertBefore(before, linkElement.firstChild);
            before = linkElement.previousSibling;
        }
        let after = linkElement.nextSibling;
        while (after && selectedNodes.includes(after)) {
            linkElement.appendChild(after);
            after = linkElement.nextSibling;
        }
        this.dependencies.selection.setCursorEnd(linkElement);
    }

    /**
     * Remove the link from the collapsed selection
     */
    removeLinkInDocument() {
        const link = this.linkInDocument;
        const cursors = this.dependencies.selection.preserveSelection();
        if (link && link.isContentEditable) {
            cursors.update(callbacksForCursorUpdate.unwrap(link));
            unwrapContents(link);
        }
        cursors.restore();
        this.linkInDocument = null;
        this.dependencies.history.addStep();
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
            if (!classes.length && !attributes.length && link.parentElement.isContentEditable) {
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
                const url = match[2] ? match[0] : "https://" + match[0];
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
        let { targetNode, targetOffset, blockToSplit } = params;
        if (targetNode.tagName !== "A") {
            return;
        }
        const edge = isPositionAtEdgeofLink(targetNode, targetOffset);
        if (!edge) {
            return;
        }
        [targetNode, targetOffset] = edge === "start" ? leftPos(targetNode) : rightPos(targetNode);
        blockToSplit = targetNode;
        splitOrLineBreakCallback({ ...params, targetNode, targetOffset, blockToSplit });
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
