import { Plugin } from "@html_editor/plugin";
import { unwrapContents } from "@html_editor/utils/dom";
import { closestElement, descendants, selectElements } from "@html_editor/utils/dom_traversal";
import { findInSelection, callbacksForCursorUpdate } from "@html_editor/utils/selection";
import { _t } from "@web/core/l10n/translation";
import { LinkPopover } from "./link_popover";
import { DIRECTIONS, leftPos, nodeSize, rightPos } from "@html_editor/utils/position";
import { EMAIL_REGEX, URL_REGEX, cleanZWChars, deduceURLfromText } from "./utils";
import { isElement, isVisible, isZwnbsp } from "@html_editor/utils/dom_info";
import { KeepLast } from "@web/core/utils/concurrency";
import { rpc } from "@web/core/network/rpc";
import { memoize } from "@web/core/utils/functions";
import { withSequence } from "@html_editor/utils/resource";
import { isBlock, closestBlock } from "@html_editor/utils/blocks";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";

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
                preview_url: urlParsed.href,
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
        return (
            await ormService.read("ir.attachment", [attachementId], ["name", "mimetype", "type"])
        )[0];
    } catch {
        return { name: url };
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
        "baseContainer",
        "feff",
        "toolbar",
    ];
    static defaultConfig = {
        allowStripDomain: true,
    };
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
                isAvailable: (selection) => {
                    const linkEl = findInSelection(selection, "a");
                    return linkEl
                        ? this.getResource("link_popovers").some((p) => p.isAvailable(linkEl))
                        : isHtmlContentSupported(selection);
                },
            },
            {
                id: "removeLinkFromSelection",
                title: _t("Remove Link"),
                description: _t("Remove Link"),
                icon: "fa-unlink",
                isAvailable: (selection) => {
                    const linkEl = findInSelection(selection, "a");
                    return (
                        !!linkEl &&
                        !this.isLinkImmutable(linkEl) &&
                        !this.isUnremovable(linkEl) &&
                        isHtmlContentSupported(selection)
                    );
                },
                run: this.removeLinkFromSelection.bind(this),
            },
        ],

        toolbar_groups: [
            withSequence(40, { id: "link", namespaces: ["compact", "expanded"] }),
            withSequence(30, { id: "image_link", namespaces: ["image"] }),
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

        power_buttons: withSequence(10, {
            commandId: "openLinkTools",
            commandParams: { type: "primary" },
            description: _t("Add a button"),
            icon: "fa-square",
        }),

        link_popovers: [
            withSequence(50, {
                //Default option
                PopoverClass: LinkPopover,
                isAvailable: (linkEl) => !linkEl || !this.isLinkImmutable(linkEl),
                getProps: (props) => props,
            }),
        ],

        immutable_link_selectors: [
            '[data-bs-toggle="tab"]',
            '[data-bs-toggle="collapse"]',
            '[data-bs-toggle="dropdown"]',
            ".dropdown-item",
            "[data-oe-model]",
            ":has(>[data-oe-model])",
        ],

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
        after_insert_handlers: this.handleAfterInsert.bind(this),

        /** Overrides */
        split_element_block_overrides: this.handleSplitBlock.bind(this),
        insert_line_break_element_overrides: this.handleInsertLineBreak.bind(this),
        delete_image_overrides: this.deleteImageLink.bind(this),
    };

    setup() {
        this.initializePopovers();
        this.currentOverlay = this.getActivePopover().overlay;
        this.addDomListener(this.editable, "click", (ev) => {
            const linkEl = ev.target.closest("a");
            if (linkEl) {
                if (ev.ctrlKey || ev.metaKey) {
                    window.open(linkEl.href, "_blank");
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
        this.addDomListener(this.editable, "auxclick", (ev) => {
            if (ev.button === 1) {
                const link = closestElement(ev.target, "a");
                if (link?.href) {
                    window.open(link.href, "_blank");
                    ev.preventDefault();
                }
            }
        });
        // link creation is added to the command service because of a shortcut conflict,
        // as ctrl+k is used for invoking the command palette
        this.unregisterLinkCommandCallback = this.services.command?.add(
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
                isAvailable: () => {
                    const selectionData = this.dependencies.selection.getSelectionData();
                    return (
                        selectionData.documentSelectionIsInEditable &&
                        isHtmlContentSupported(selectionData.editableSelection)
                    );
                },
            }
        );
        this.ignoredClasses = new Set(this.getResource("system_classes"));

        this.getExternalMetaData = memoize(fetchExternalMetaData);
        this.getInternalMetaData = memoize(fetchInternalMetaData);
        this.getAttachmentMetadata = memoize((url) =>
            fetchAttachmentMetaData(url, this.services.orm)
        );
        this.LinkPopoverState = { editing: false };
        this.newlyInsertedLinks = new Set();
    }

    destroy() {
        this.unregisterLinkCommandCallback?.();
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
        if (url !== undefined) {
            link.setAttribute("href", url);
        }
        for (const [param, value] of Object.entries(this.config.defaultLinkAttributes || {})) {
            link.setAttribute(param, `${value}`);
        }
        link.innerText = label;
        this.dispatchTo("create_link_handlers", link);
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
        if (this.getResource("link_compatible_selection_predicates").some((p) => p())) {
            return true;
        }
        const linksInSelection = this.dependencies.selection
            .getTargetedNodes()
            .filter((n) => n.tagName === "A");
        const targetedNodes = this.dependencies.selection.getTargetedNodes();
        return (
            linksInSelection.length < 2 &&
            // Prevent a link across sibling blocks:
            !targetedNodes.some((node) => {
                const next = node.nextSibling;
                const previous = node.previousSibling;
                return (
                    (next && targetedNodes.includes(next) && isBlock(next)) ||
                    (previous && targetedNodes.includes(previous) && isBlock(previous))
                );
            })
        );
    }

    /**
     * open the Link popover to edit links
     *
     * @param {HTMLElement} [linkElement]
     */
    openLinkTools(linkElement, type) {
        this.currentOverlay.close();
        this.LinkPopoverState.editing = false;
        if (!this.isLinkAllowedOnSelection()) {
            return this.services.notification.add(
                _t("Unable to create a link on the current selection."),
                { type: "danger" }
            );
        }
        this.dependencies.toolbar.closeToolbar();
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
            linkElement = this.createLink(undefined, selection.textContent());
        }

        const selectionTextContent = selection?.textContent();
        const isImage = !!findInSelection(selection, "img");

        const applyCallback = (url, label, classes, customStyle, linkTarget, attachmentId) => {
            if (this.linkInDocument) {
                if (url) {
                    this.linkInDocument.href = url;
                } else {
                    this.linkInDocument.removeAttribute("href");
                }
                if (linkTarget) {
                    this.linkInDocument.setAttribute("target", linkTarget);
                } else {
                    this.linkInDocument.removeAttribute("target");
                }
                if (!isImage) {
                    if (classes) {
                        this.linkInDocument.className = classes;
                    } else {
                        this.linkInDocument.removeAttribute("class");
                    }
                    if (customStyle) {
                        this.linkInDocument.setAttribute("style", customStyle);
                    } else {
                        this.linkInDocument.removeAttribute("style");
                    }
                    if (
                        this.linkInDocument.childElementCount == 0 &&
                        cleanZWChars(this.linkInDocument.innerText) !== label
                    ) {
                        this.linkInDocument.innerText = label;
                        cursorsToRestore = null;
                    }
                }
            } else if (url) {
                // prevent the link creation if the url field was empty

                // create a new link with current selection as a content
                if ((selectionTextContent && selectionTextContent === label) || isImage) {
                    const link = this.createLink(url);
                    if (classes) {
                        link.className = classes;
                    }
                    const image = isImage && findInSelection(selection, "img");
                    const figure =
                        image?.parentElement?.matches("figure[contenteditable=false]") &&
                        image.parentElement;
                    if (figure) {
                        figure.before(link);
                        link.append(figure);
                        if (link.parentElement === this.editable) {
                            const baseContainer =
                                this.dependencies.baseContainer.createBaseContainer();
                            link.before(baseContainer);
                            baseContainer.append(link);
                        }
                    } else {
                        const content = this.dependencies.selection.extractContent(selection);
                        link.append(content);
                        link.normalize();
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
                    }
                    this.linkInDocument = link;
                } else if (label) {
                    const link = this.createLink(url, label);
                    if (classes) {
                        link.className = classes;
                    }
                    if (customStyle) {
                        link.setAttribute("style", customStyle);
                    }
                    if (linkTarget) {
                        link.setAttribute("target", linkTarget);
                    }
                    this.linkInDocument = link;
                    cursorsToRestore = null;
                    this.dependencies.dom.insert(link);
                }
            }
            if (attachmentId) {
                this.linkInDocument.dataset.attachmentId = attachmentId;
            }
        };

        this.restoreSavePoint = this.dependencies.history.makeSavePoint();
        const props = {
            document: this.document,
            linkElement,
            isImage: isImage,
            onApply: (...args) => {
                delete this._isNavigatingByMouse;
                applyCallback(...args);
                this.closeLinkTools(cursorsToRestore);
                this.dependencies.selection.focusEditable();
                this.dependencies.history.addStep();
            },
            onChange: applyCallback,
            onDiscard: () => {
                this.restoreSavePoint();
                if (linkElement.isConnected) {
                    this.openLinkTools(linkElement);
                } else {
                    this.linkInDocument = null;
                    this.currentOverlay.close();
                }
                this.dependencies.selection.focusEditable();
            },
            onRemove: () => {
                this.removeLinkInDocument();
                this.linkInDocument = null;
                this.currentOverlay.close();
            },
            onCopy: () => {
                this.linkInDocument = null;
                this.currentOverlay.close();
            },
            onEdit: () => {
                this.restoreSavePoint = this.dependencies.history.makeSavePoint();
            },
            getInternalMetaData: this.getInternalMetaData,
            getExternalMetaData: this.getExternalMetaData,
            getAttachmentMetadata: this.getAttachmentMetadata,
            recordInfo: this.config.getRecordInfo?.() || {},
            canEdit:
                !this.linkInDocument || !this.linkInDocument.classList.contains("o_link_readonly"),
            canRemove: this.linkInDocument && !this.isUnremovable(this.linkInDocument),
            canUpload: this.config.allowFile,
            onUpload: this.config.onAttachmentChange,
            type: this.type || "",
            LinkPopoverState: this.LinkPopoverState,
            showReplaceTitleBanner: this.newlyInsertedLinks.has(linkElement),
            allowCustomStyle: this.config.allowCustomStyle,
            allowTargetBlank: this.config.allowTargetBlank,
            allowStripDomain: this.config.allowStripDomain,
        };

        const popover = this.getActivePopover(linkElement);
        if (popover) {
            this.currentOverlay = popover.overlay;
            if (!linkElement.href) {
                this.LinkPopoverState.editing = true;
            }
            this.currentOverlay.open({ props: popover.getProps(props) });
            if (this.linkInDocument) {
                if (this.newlyInsertedLinks.has(this.linkInDocument)) {
                    this.newlyInsertedLinks.delete(this.linkInDocument);
                }
            }
        }
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
        if (this.currentOverlay.isOpen && document.querySelector(".o-we-linkpopover")) {
            this.currentOverlay.close();
            if (link && link.isConnected) {
                this.dependencies.selection.setSelection({
                    anchorNode: link,
                    anchorOffset: 0,
                    focusNode: link,
                    focusOffset: nodeSize(link),
                });
                const saveCustomStyle = link.getAttribute("style");
                link.removeAttribute("style");
                this.dependencies.color.removeAllColor();
                if (
                    saveCustomStyle &&
                    this.config.allowCustomStyle &&
                    link.className.includes("custom")
                ) {
                    link.setAttribute("style", saveCustomStyle);
                }
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
            if (/btn(-[a-z0-9_-]*)custom/.test(anchorEl.className)) {
                // if the link is a customized button, we don't want to change the color
                continue;
            }
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
        if (!selectionData.currentSelectionIsInEditable) {
            const anchorNode = document.getSelection()?.anchorNode;
            if (anchorNode && isElement(anchorNode) && anchorNode.closest(".o-we-linkpopover")) {
                return;
            }
            this.linkInDocument = null;
            this.closeLinkTools();
        } else if (!selection.isCollapsed) {
            // Open the link tool only if we have an image selected and the selection
            // is fully contained in the image parent link.
            const imageNode = findInSelection(selection, "img");
            const parentElement = imageNode?.parentElement;
            const linkContainingImage = imageNode && closestElement(imageNode, "a");
            if (
                linkContainingImage &&
                this.isLinkAllowedOnSelection() &&
                parentElement.contains(selection.anchorNode) &&
                parentElement.contains(selection.focusNode)
            ) {
                this.openLinkTools(linkContainingImage);
            } else {
                this.linkInDocument = null;
                this.closeLinkTools();
            }
        } else {
            const closestLinkElement = closestElement(selection.anchorNode, "A");
            const isLinkEditable = this.delegateTo(
                "is_link_editable_predicates",
                closestLinkElement) || false;
            if (closestLinkElement && closestLinkElement.isContentEditable) {
                if (closestLinkElement !== this.linkInDocument || !this.currentOverlay.isOpen) {
                    this.openLinkTools(closestLinkElement);
                }
            } else if (isLinkEditable) {
                this.openLinkTools(closestLinkElement);
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
     * @return {boolean}
     */
    extendLinkToSelection(linkElement) {
        this.dependencies.split.splitSelection();
        const selectedNodes = this.dependencies.selection.getTargetedNodes();
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

    isUnremovable(linkEl) {
        return this.getResource("unremovable_node_predicates").some((p) => p(linkEl));
    }

    /**
     * Remove the link from the collapsed selection
     */
    removeLinkInDocument(link = this.linkInDocument) {
        if (this.isUnremovable(link)) {
            return;
        }
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
                const figure = closestElement(imageNode, "figure");
                if (direction === DIRECTIONS.RIGHT) {
                    imageLink = this.dependencies.split.splitAroundUntil(
                        figure || imageNode,
                        endLink
                    );
                } else {
                    imageLink = this.dependencies.split.splitAroundUntil(
                        figure || imageNode,
                        startLink
                    );
                }
                cursors.update(callbacksForCursorUpdate.unwrap(imageLink));
                unwrapContents(imageLink);
                if (figure && figure.parentElement !== this.editable) {
                    // Remove the base container parent if there is one. Figure
                    // is a block so it's not needed.
                    unwrapContents(figure.parentElement);
                }
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
                if (this.currentOverlay.isOpen) {
                    this.currentOverlay.close();
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
            isHtmlContentSupported(selection) &&
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

    handleAfterInsert(insertedNodes) {
        for (const node of insertedNodes) {
            if (node.nodeType === Node.ELEMENT_NODE) {
                for (const link of selectElements(node, "A")) {
                    if (link.getAttribute("href") === link.textContent && !this.isImage) {
                        this.newlyInsertedLinks.add(link);
                    }
                }
            }
        }
    }

    initializePopovers() {
        this.overlays = [];
        this.getResource("link_popovers").map((link_popover) => {
            this.overlays.push({
                overlay: this.dependencies.overlay.createOverlay(
                    link_popover.PopoverClass,
                    {
                        closeOnPointerdown: true,
                    },
                    {
                        sequence: 50,
                    }
                ),
                isAvailable: link_popover.isAvailable,
                getProps: link_popover.getProps,
            });
        });
    }

    getActivePopover(linkElement) {
        return this.overlays.find((overlay) => overlay.isAvailable(linkElement));
    }

    isLinkImmutable(linkEl) {
        return this.getResource("immutable_link_selectors").some((s) => linkEl.matches(s));
    }
}
