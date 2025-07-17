import { Plugin } from "@html_editor/plugin";
import { unwrapContents } from "@html_editor/utils/dom";
import { closestElement, descendants, selectElements } from "@html_editor/utils/dom_traversal";
import { findInSelection, callbacksForCursorUpdate } from "@html_editor/utils/selection";
import { _t } from "@web/core/l10n/translation";
import { LinkPopover } from "./link_popover";
import { DIRECTIONS, leftPos, nodeSize, rightPos } from "@html_editor/utils/position";
import { EMAIL_REGEX, URL_REGEX, cleanZWChars, deduceURLfromText } from "./utils";
import { isVisible, isZwnbsp } from "@html_editor/utils/dom_info";
import { KeepLast } from "@web/core/utils/concurrency";
import { rpc } from "@web/core/network/rpc";
import { memoize } from "@web/core/utils/functions";
import { withSequence } from "@html_editor/utils/resource";
import { isBlock, closestBlock } from "@html_editor/utils/blocks";

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
    if (!childNodes.length) {
        return "end";
    }
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
    // Enforce the current page's protocol to prevent mixed content issues.
    if (urlParsed.protocol !== window.location.protocol) {
        urlParsed.protocol = window.location.protocol;
    }

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
        "feff",
        "linkSelection",
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
                run: ({ link, type } = {}) => this.openLinkTools(link, type),
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
        input_handlers: this.onInputDeleteNormalizeLink.bind(this),
        before_delete_handlers: this.updateCurrentLinkSyncState.bind(this),
        delete_handlers: this.onInputDeleteNormalizeLink.bind(this),
        before_paste_handlers: this.updateCurrentLinkSyncState.bind(this),
        after_paste_handlers: this.onPasteNormalizeLink.bind(this),
        selectionchange_handlers: this.handleSelectionChange.bind(this),
        clean_for_save_handlers: ({ root }) => this.removeEmptyLinks(root),
        normalize_handlers: this.normalizeLink.bind(this),

        /** Overrides */
        split_element_block_overrides: this.handleSplitBlock.bind(this),
        insert_line_break_element_overrides: this.handleInsertLineBreak.bind(this),
        delete_image_overrides: this.deleteImageLink.bind(this),
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
        this.addDomListener(this.editable, "mousedown", () => {
            this._isNavigatingByMouse = true;
        });
        this.addDomListener(this.editable, "keydown", () => {
            delete this._isNavigatingByMouse;
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
        this.LinkPopoverState = { editing: false };
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
        this.overlay.close();
        this.LinkPopoverState.editing = false;
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

        const applyCallback = (url, label, classes, attachmentId) => {
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
                if (
                    this.linkInDocument.childElementCount == 0 &&
                    cleanZWChars(this.linkInDocument.innerText) !== label
                ) {
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
            if (attachmentId) {
                this.linkInDocument.dataset.attachmentId = attachmentId;
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
            LinkPopoverState: this.LinkPopoverState,
        };
        if (!linkElement.href) {
            this.LinkPopoverState.editing = true;
        }
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
                if (font && cleanZWChars(anchorEl.textContent) === font.textContent) {
                    continue;
                }
                const newFont = this.document.createElement("font");
                newFont.append(...childNodes);
                anchorEl.appendChild(newFont);
                this.dependencies.color.colorElement(newFont, color, "color");
            }

            // When a link contains unsupported element (like an iframe or a link),
            // we remove the link. Cases can happen when a image link is replaced
            // by a document or a video
            const hasUnsupportedMedia = anchorEl.querySelector("a, iframe");
            if (hasUnsupportedMedia) {
                this.removeLinkInDocument(anchorEl);
            }
        }
    }

    handleSelectionChange(selectionData) {
        const selection = selectionData.editableSelection;
<<<<<<< 43d3fbbfd6b0c5e471c6ce45e2c5ad62fae52819
||||||| 74eecadb39e0c260f4cfc1ae9478c84eda815132
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
            getAttachmentMetadata: this.getAttachmentMetadata,
            recordInfo: this.config.getRecordInfo?.() || {},
            type: this.type || "",
            LinkPopoverState: this.LinkPopoverState,
        };
=======
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
                this.removeCurrentLinkIfEmtpy();
            },
            getInternalMetaData: this.getInternalMetaData,
            getExternalMetaData: this.getExternalMetaData,
            getAttachmentMetadata: this.getAttachmentMetadata,
            recordInfo: this.config.getRecordInfo?.() || {},
            type: this.type || "",
            LinkPopoverState: this.LinkPopoverState,
        };
>>>>>>> 4488229f2b807f43332c599a0552a41079e5295d
        if (
            this._isNavigatingByMouse &&
            selection.isCollapsed &&
            selectionData.documentSelectionIsInEditable
        ) {
            delete this._isNavigatingByMouse;
            const { startContainer, startOffset, endContainer, endOffset } = selection;
            const linkElement = closestElement(startContainer, "a");
            if (
                linkElement &&
                linkElement.textContent.startsWith("\uFEFF") &&
                linkElement.textContent.endsWith("\uFEFF")
            ) {
                const linkDescendants = descendants(linkElement);

                // Check if the cursor is positioned at the begining of link.
                const isCursorAtStartOfLink = isZwnbsp(startContainer)
                    ? linkDescendants.indexOf(startContainer) === 0
                    : startContainer.nodeType === Node.TEXT_NODE &&
                      linkDescendants.indexOf(startContainer) === 1 &&
                      startOffset === 0;

                // Check if the cursor is positioned at the end of link.
                const isCursorAtEndOfLink = isZwnbsp(endContainer)
                    ? linkDescendants.indexOf(endContainer) === linkDescendants.length - 1
                    : endContainer.nodeType === Node.TEXT_NODE &&
                      linkDescendants.indexOf(endContainer) === linkDescendants.length - 2 &&
                      endOffset === nodeSize(endContainer);

                // Handle selection movement.
                if (isCursorAtStartOfLink || isCursorAtEndOfLink) {
                    const [targetNode, targetOffset] = isCursorAtStartOfLink
                        ? leftPos(linkElement)
                        : rightPos(linkElement);
                    this.dependencies.selection.setSelection({
                        anchorNode: targetNode,
                        anchorOffset: isCursorAtStartOfLink ? targetOffset - 1 : targetOffset + 1,
                    });
                    return;
                }
            }
        }
        if (!selectionData.documentSelectionIsInEditable) {
            const popoverEl = document.querySelector(".o-we-linkpopover");
            if (popoverEl?.contains(selectionData.documentSelection?.anchorNode)) {
                return;
            }
            this.linkInDocument = null;
            this.closeLinkTools();
        } else if (!selection.isCollapsed) {
            // Open the link tool only if we have an image selected and the selection
            // is fully contained in the image parent link.
            const imageNode = findInSelection(selection, "img");
            const parentElement = imageNode?.parentElement;
            if (
                imageNode?.parentNode?.tagName === "A" &&
                this.isLinkAllowedOnSelection() &&
                parentElement.contains(selection.anchorNode) &&
                parentElement.contains(selection.focusNode)
            ) {
                this.openLinkTools(imageNode.parentElement);
            } else {
                this.linkInDocument = null;
                this.closeLinkTools();
            }
        } else {
<<<<<<< 43d3fbbfd6b0c5e471c6ce45e2c5ad62fae52819
            const closestLinkElement = closestElement(selection.anchorNode, "A");
            if (closestLinkElement) {
                if (closestLinkElement !== this.linkInDocument) {
                    this.openLinkTools(closestLinkElement);
||||||| 74eecadb39e0c260f4cfc1ae9478c84eda815132
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
                this.LinkPopoverState.editing = false;
            }

            // if the link includes an inline image, we close the previous opened popover to reposition it
            const imageNode = linkEl.querySelector("img");
            if (imageNode) {
                this.removeCurrentLinkIfEmtpy();
                this.overlay.close();
            }

            if (linkEl.isConnected) {
                const linkProps = {
                    ...props,
                    isImage: false,
                    linkEl: this.linkElement,
                    onApply: (url, label, classes, attachmentId) => {
                        this.linkElement.href = url;
                        if (attachmentId) {
                            this.linkElement.dataset.attachmentId = attachmentId;
                        }
                        if (
                            cleanZWChars(this.linkElement.innerText) === label ||
                            !!this.linkElement.childElementCount
                        ) {
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
                        cleanTrailingBR(closestBlock(this.linkElement));
                        this.dependencies.selection.focusEditable();
                        this.removeCurrentLinkIfEmtpy();
                        this.LinkPopoverState.editing = false;
                        this.dependencies.history.addStep();
                    },
                    canEdit: !this.linkElement.classList.contains("o_link_readonly"),
                    canUpload: !this.config.disableFile,
                    onUpload: this.config.onAttachmentChange,
                };
                if (!this.linkElement.href) {
                    this.LinkPopoverState.editing = true;
=======
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
                this.LinkPopoverState.editing = false;
            }

            if (this.linkElement && this.linkElement.classList.contains("o_link_in_selection")) {
                this.dependencies.linkSelection.padLinkWithZwnbsp(this.linkElement);
            }

            // if the link includes an inline image, we close the previous opened popover to reposition it
            const imageNode = linkEl.querySelector("img");
            if (imageNode) {
                this.removeCurrentLinkIfEmtpy();
                this.overlay.close();
            }

            if (linkEl.isConnected) {
                const linkProps = {
                    ...props,
                    isImage: false,
                    linkEl: this.linkElement,
                    onApply: (url, label, classes, attachmentId) => {
                        this.linkElement.href = url;
                        if (attachmentId) {
                            this.linkElement.dataset.attachmentId = attachmentId;
                        }
                        if (
                            cleanZWChars(this.linkElement.innerText) === label ||
                            !!this.linkElement.childElementCount
                        ) {
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
                        cleanTrailingBR(closestBlock(this.linkElement));
                        this.dependencies.selection.focusEditable();
                        this.removeCurrentLinkIfEmtpy();
                        this.LinkPopoverState.editing = false;
                        this.dependencies.history.addStep();
                    },
                    canEdit: !this.linkElement.classList.contains("o_link_readonly"),
                    canUpload: !this.config.disableFile,
                    onUpload: this.config.onAttachmentChange,
                };
                if (!this.linkElement.href) {
                    this.LinkPopoverState.editing = true;
>>>>>>> 4488229f2b807f43332c599a0552a41079e5295d
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
        const targetedNodes = this.dependencies.selection.getTargetedNodes();
        let before = linkElement.previousSibling;
        while (before !== null && targetedNodes.includes(before)) {
            linkElement.insertBefore(before, linkElement.firstChild);
            before = linkElement.previousSibling;
        }
        let after = linkElement.nextSibling;
        while (after && targetedNodes.includes(after)) {
            linkElement.appendChild(after);
            after = linkElement.nextSibling;
        }
        this.dependencies.selection.setCursorEnd(linkElement);
    }

    /**
     * Remove the link from the collapsed selection
     */
    removeLinkInDocument(link = this.linkInDocument) {
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

        // If not, unlink only the part(s) of the link(s) that are selected:
        // `<a>a[b</a>c<a>d</a>e<a>f]g</a>` => `<a>a</a>[bcdef]<a>g</a>`.
        let { anchorNode, focusNode, anchorOffset, focusOffset } = selection;
        const direction = selection.direction;
        // Split the links around the selection.
        let [startLink, endLink] = [
            closestElement(anchorNode, "a"),
            closestElement(focusNode, "a"),
        ];
        let cursors;
        if (startLink) {
            // If a FEFF character is present as anchorNode or focusNode,
            // restoring the selection later may throw an error. Therefore,
            // FEFF characters should be cleaned before splitting the link.
            cursors = this.dependencies.selection.preserveSelection();
            this.dependencies.feff.removeFeffs(startLink, cursors);
            cursors.restore();
        }
        if (endLink && startLink !== endLink) {
            cursors = this.dependencies.selection.preserveSelection();
            this.dependencies.feff.removeFeffs(endLink, cursors);
            cursors.restore();
        }
        ({ anchorNode, focusNode, anchorOffset, focusOffset } =
            this.dependencies.selection.getEditableSelection());
        cursors = this.dependencies.selection.preserveSelection();
        // to remove link from selected images
        let targetedNodes = this.dependencies.selection.getTargetedNodes();
        const selectedImageNodes = targetedNodes.filter((node) => node.tagName === "IMG");
        if (selectedImageNodes.length && startLink && endLink && startLink === endLink) {
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
                selectedImageNodes.length === targetedNodes.length
            ) {
                this.dependencies.history.addStep();
                return;
            }
        }
        const startBlock = closestBlock(startLink);
        const endBlock = closestBlock(endLink);
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
        targetedNodes = this.dependencies.selection.getTargetedNodes();
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
        if (startBlock) {
            // Remove empty links splitted by `splitAroundUntil` due to
            // adjacent invisible text nodes.
            this.removeEmptyLinks(startBlock);
        }
        if (endBlock && endBlock !== startBlock) {
            this.removeEmptyLinks(endBlock);
        }
        this.dependencies.history.addStep();
    }

    removeEmptyLinks(root) {
        // @todo: check for unremovables
        // @todo: preserve spaces
        const buttonClassRegex =
            /^(btn|btn-(sm|lg|(?:[a-z0-9_]+-)?(?:primary|secondary))|rounded-circle)$/;
        for (const link of root.querySelectorAll("a")) {
            if ([...link.childNodes].some(isVisible)) {
                continue;
            }
            const classes = [...link.classList].filter(
                (c) => !this.ignoredClasses.has(c) && !buttonClassRegex.test(c)
            );
            const attributes = [...link.attributes].filter(
                (a) => !["style", "href", "class"].includes(a.name)
            );
            if (!classes.length && !attributes.length && link.parentElement.isContentEditable) {
                link.remove();
            }
        }
    }

    updateCurrentLinkSyncState() {
        const { anchorNode } = this.dependencies.selection.getEditableSelection();
        const linkEl = closestElement(anchorNode, "a");
        if (linkEl && linkEl.isContentEditable) {
            const label = linkEl.innerText;
            const url = deduceURLfromText(label, linkEl);
            const href = linkEl.getAttribute("href");
            if (
                url &&
                (url === href || url + "/" === href || url === deduceURLfromText(href, linkEl))
            ) {
                this.isCurrentLinkInSync = true;
            }
        }
    }

    onBeforeInput(ev) {
        if (ev.inputType === "insertParagraph" || ev.inputType === "insertLineBreak") {
            const nodeForSelectionRestore = this.handleAutomaticLinkInsertion();
            if (nodeForSelectionRestore) {
                this.dependencies.selection.setCursorStart(nodeForSelectionRestore);
                this.dependencies.history.addStep();
            }
        }
        if (ev.inputType === "insertText" && ev.data === " ") {
            const nodeForSelectionRestore = this.handleAutomaticLinkInsertion();
            if (nodeForSelectionRestore) {
                // Since we manually insert a space here, we will be adding a history step
                // after link creation with selection at the end of the link and another
                // after inserting the space. So first undo will remove the space, and the
                // second will undo the link creation.
                this.dependencies.selection.setSelection({
                    anchorNode: nodeForSelectionRestore,
                    anchorOffset: 0,
                });
                this.dependencies.history.addStep();
                nodeForSelectionRestore.textContent =
                    "\u00A0" + nodeForSelectionRestore.textContent;
                this.dependencies.selection.setSelection({
                    anchorNode: nodeForSelectionRestore,
                    anchorOffset: 1,
                });
                this.dependencies.history.addStep();
                ev.preventDefault();
            }
        }
        this.updateCurrentLinkSyncState();
    }

    onInputDeleteNormalizeLink() {
        const { anchorNode } = this.dependencies.selection.getEditableSelection();
        const linkEl = closestElement(anchorNode, "a");
        if (linkEl && linkEl.isContentEditable) {
            const label = linkEl.innerText;
            const url = deduceURLfromText(label, linkEl);
            if (url && this?.isCurrentLinkInSync) {
                linkEl.setAttribute("href", url);
                this.isCurrentLinkInSync = false;
                if (this.overlay.isOpen) {
                    this.overlay.close();
                }
            }
        }
    }
    onPasteNormalizeLink() {
        this.updateCurrentLinkSyncState();
        this.onInputDeleteNormalizeLink();
    }

    deleteImageLink(imageToDelete) {
        if (imageToDelete.parentElement.tagName === "A") {
            // If the link is empty after removing the image, remove it.
            const cursors = this.dependencies.selection.preserveSelection();
            cursors.update(callbacksForCursorUpdate.remove(imageToDelete));
            imageToDelete.remove();
            this.closeLinkTools(cursors);
            this.dependencies.history.addStep();
            return true;
        }
        return false;
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
                return nodeForSelectionRestore;
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
