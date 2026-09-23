/** @odoo-module native */
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { Plugin } from "@html_editor/plugin";
import { closestBlock, isBlock } from "@html_editor/utils/blocks";
import { mergeAdjacentTextNodes, unwrapContents } from "@html_editor/utils/dom";
import {
    isElement,
    isProtected,
    isProtecting,
    isVisible,
    isZwnbsp,
} from "@html_editor/utils/dom_info";
import {
    closestElement,
    descendants,
    selectElements,
} from "@html_editor/utils/dom_traversal";
import { DIRECTIONS, leftPos, nodeSize, rightPos } from "@html_editor/utils/position";
import { withSequence } from "@html_editor/utils/resource";
import {
    callbacksForCursorUpdate,
    findInSelection,
} from "@html_editor/utils/selection";
import { isBrowserFirefox } from "@web/core/browser/feature_detection";
import { rpc } from "@web/core/network";
import { _t } from "@web/core/translation";
import { KeepLast } from "@web/core/utils/concurrency";
import { memoize } from "@web/core/utils/functions";

import { LinkPopover } from "./link_popover.js";
import { cleanZWChars, deduceURLfromText, EMAIL_REGEX, URL_REGEX } from "./utils.js";

/** @typedef {import("@odoo/owl").Component} Component */
/** @typedef {import("plugins").CSSSelector} CSSSelector */
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
 * A click on a `label` belongs to its input and a click on a `button` to its
 * action; a link nested in either one swallows that click instead. So the
 * editor stops offering to create one there.
 *
 * @param {Node} node
 */
function allowedToCreateLink(node) {
    return !closestElement(node, "label, button");
}

/**
 * @param {EditorSelection} selection
 */
export function isLinkSupported(selection) {
    return (
        isHtmlContentSupported(selection) && allowedToCreateLink(selection.anchorNode)
    );
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
    lastVisibleIndex =
        lastVisibleIndex === -1 ? 0 : childNodes.length - lastVisibleIndex;
    if (offset >= lastVisibleIndex) {
        return "end";
    }
    return false;
}

async function fetchExternalMetaData(url) {
    try {
        return await rpc("/html_editor/link_preview_external", {
            preview_url: url,
        });
    } catch {
        return;
    }
}

async function fetchInternalMetaData(url) {
    const keepLastPromise = new KeepLast();
    const urlParsed = new URL(url);
    if (urlParsed.protocol !== window.location.protocol) {
        urlParsed.protocol = window.location.protocol;
    }

    const result = await keepLastPromise
        .add(fetch(urlParsed))
        .then((response) => response.text())
        .then(async (content) => {
            const html_parser = new window.DOMParser();
            const doc = html_parser.parseFromString(content, "text/html");
            const internalUrlMetaData = await rpc(
                "/html_editor/link_preview_internal",
                {
                    preview_url: urlParsed.href,
                },
            );

            internalUrlMetaData["favicon"] = doc.querySelector("link[rel~='icon']");
            internalUrlMetaData["ogTitle"] = doc.querySelector("[property='og:title']");
            internalUrlMetaData["title"] = doc.querySelector("title");

            return internalUrlMetaData;
        })
        .catch((error) => {
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
            await ormService.read(
                "ir.attachment",
                [attachementId],
                ["name", "mimetype", "type"],
            )
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

/**
 * @typedef {((link: HTMLLinkElement) => boolean)[]} is_link_editable_predicates
 * @typedef {((link: HTMLLinkElement) => boolean)[]} legit_empty_link_predicates
 * @typedef {(() => boolean)[]} link_compatible_selection_predicates
 * @typedef {CSSSelector[]} immutable_link_selectors
 * @typedef {{
 * PopoverClass: Component;
 * isAvailable: (linkEl: HTMLLinkElement) => boolean;
 * getProps: (props) => props;
 * }[]} link_popovers
 * @typedef {((linkEl: HTMLAnchorElement) => void)[]} create_link_handlers
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
    ];
    static defaultConfig = {
        allowStripDomain: true,
    };
    static shared = ["createLink", "insertLink", "getPathAsUrlCommand"];
    /** @type {import("plugins").EditorResources} */
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
                        ? this.getResource("link_popovers").some((p) =>
                              p.isAvailable(linkEl),
                          )
                        : isLinkSupported(selection);
                },
            },
            {
                id: "removeLinkFromSelection",
                title: _t("Remove Link"),
                description: _t("Remove Link"),
                icon: "fa-unlink",
                isAvailable: (selection) => {
                    if (!isHtmlContentSupported(selection)) {
                        return false;
                    }
                    for (const node of this.dependencies.selection.getTargetedNodes()) {
                        const linkEl = closestElement(node, "a");
                        if (
                            linkEl &&
                            !this.isLinkImmutable(linkEl) &&
                            linkEl.parentElement.isContentEditable
                        ) {
                            return true;
                        }
                    }
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
                isDisabled: () => this.removeLinkFromSelectionIsDisabled(),
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
                isDisabled: () => this.removeLinkFromSelectionIsDisabled(),
            },
        ],

        powerbox_categories: withSequence(50, {
            id: "navigation",
            name: _t("Navigation"),
        }),
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
            ".o_prevent_link_editor a",
        ],
        legit_empty_link_predicates: (linkEl) => linkEl.hasAttribute("data-mimetype"),
        unsplittable_node_predicates: (node) => node.nodeName === "A",
        fully_selected_node_predicates: (node, selection) =>
            node.nodeName === "A" &&
            !node.classList.contains("btn") &&
            cleanZWChars(selection.textContent()) === cleanZWChars(node.innerText),

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
        on_will_remove_handlers: () => this.closeLinkTools(),

        split_element_block_overrides: this.handleSplitBlock.bind(this),
        insert_line_break_element_overrides: this.handleInsertLineBreak.bind(this),
        delete_image_overrides: this.deleteImageLink.bind(this),
        delete_backward_overrides: withSequence(
            15,
            this.handleDeleteBackward.bind(this),
        ),
        double_click_overrides: this.doubleClickLinkOverrides.bind(this),
        triple_click_overrides: this.tripleClickButtonOverrides.bind(this),

        to_inline_code_processors: (node) => {
            this.removeEmptyLinks(node);
            for (const btn of selectElements(node, "a.btn")) {
                [...btn.attributes].forEach(
                    (attr) => attr.name !== "href" && btn.removeAttribute(attr.name),
                );
            }
        },
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
        this.unregisterLinkCommandCallback = this.services.command?.add(
            "Create link",
            () => {
                this.dependencies.selection.focusEditable();
                setTimeout(() => this.openLinkTools());
            },
            {
                hotkey: "control+k",
                category: "shortcut_conflict",
                isAvailable: () => {
                    const selectionData =
                        this.dependencies.selection.getSelectionData();
                    return (
                        selectionData.documentSelectionIsInEditable &&
                        isHtmlContentSupported(selectionData.editableSelection) &&
                        this.isLinkAllowedOnSelection()
                    );
                },
            },
        );

        this.getExternalMetaData = memoize(fetchExternalMetaData);
        this.getInternalMetaData = memoize(fetchInternalMetaData);
        this.getAttachmentMetadata = memoize((url) =>
            fetchAttachmentMetaData(url, this.services.orm),
        );
        this.LinkPopoverState = { editing: false };
        this.newlyInsertedLinks = new Set();
    }

    destroy() {
        this.unregisterLinkCommandCallback?.();
    }

    /**
     * @param {string} url
     * @param {string} label
     * @return {HTMLElement}
     */
    createLink(url, label = "") {
        const link = this.document.createElement("a");
        if (url !== undefined) {
            link.setAttribute("href", url);
        }
        for (const [param, value] of Object.entries(
            this.config.defaultLinkAttributes || {},
        )) {
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
            { normalize: false },
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
                this.dispatchTo(
                    "before_paste_handlers",
                    this.dependencies.selection.getEditableSelection(),
                );
                this.dependencies.dom.insert(this.createLink(url, text));
                this.dependencies.history.addStep();
            },
        };
        return pasteAsURLCommand;
    }

    isLinkAllowedOnSelection() {
        const fromPredicates = this.checkPredicates(
            "link_compatible_selection_predicates",
        );
        if (fromPredicates !== undefined) {
            return fromPredicates;
        }
        const targetedNodes = this.dependencies.selection.getTargetedNodes();
        const targetedBlocks = targetedNodes.filter(isBlock);
        const linksInSelection = targetedNodes.filter((n) => n.tagName === "A");
        return (
            linksInSelection.length < 2 &&
            targetedBlocks.every((node) =>
                targetedNodes.every(
                    (other) => node.contains(other) || other.contains(node),
                ),
            )
        );
    }

    /**
     * @param {HTMLElement} [linkElement]
     */
    openLinkTools(linkElement, type) {
        this.currentOverlay.close();
        this.LinkPopoverState.editing = false;
        if (!this.isLinkAllowedOnSelection()) {
            return this.services.notification.add(
                _t("Unable to create a link on the current selection."),
                { type: "danger" },
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
            this.extendLinkToSelection(linkElement);
            linkElement = findInSelection(selection, "a");
            this.dependencies.history.addStep();
            cursorsToRestore = this.dependencies.selection.preserveSelection();
        }
        this.linkInDocument = linkElement;
        if (!linkElement) {
            linkElement = this.createLink(undefined, selection.textContent());
        }

        const selectionTextContent = selection?.textContent();
        const isImage = !!findInSelection(selection, "img");

        const applyCallback = (
            url,
            label,
            classes,
            customStyle,
            linkTarget,
            attachmentId,
            relValue,
        ) => {
            if (this.linkInDocument) {
                if (url) {
                    this.linkInDocument.href = url;
                } else {
                    this.linkInDocument.removeAttribute("href");
                }
                if (relValue) {
                    this.linkInDocument.setAttribute("rel", relValue);
                } else {
                    this.linkInDocument.removeAttribute("rel");
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
                        this.linkInDocument.childElementCount === 0 &&
                        cleanZWChars(this.linkInDocument.innerText) !== label
                    ) {
                        this.linkInDocument.innerText = label;
                        cursorsToRestore = null;
                    }
                }
            } else if (url) {
                if (
                    (selectionTextContent && selectionTextContent === label) ||
                    isImage
                ) {
                    const link = this.createLink(url);
                    if (relValue) {
                        link.setAttribute("rel", relValue);
                    }
                    const image = isImage && findInSelection(selection, "img");
                    const figure =
                        image?.parentElement?.matches(
                            "figure[contenteditable=false]",
                        ) && image.parentElement;
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
                        const content =
                            this.dependencies.selection.extractContent(selection);
                        link.append(content);
                        link.normalize();
                        cursorsToRestore = null;
                        selection = this.dependencies.selection.getEditableSelection();
                        const anchorClosestElement = closestElement(
                            selection.anchorNode,
                        );
                        if (commonAncestor !== anchorClosestElement) {
                            const [anchorNode, anchorOffset] =
                                rightPos(anchorClosestElement);
                            this.dependencies.selection.setSelection(
                                { anchorNode, anchorOffset },
                                { normalize: false },
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
                !this.linkInDocument ||
                !this.linkInDocument.classList.contains("o_link_readonly"),
            canRemove:
                this.linkInDocument &&
                this.linkInDocument.parentElement.isContentEditable &&
                !this.isUnremovable(this.linkInDocument),
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

    closeLinkTools(cursors = null) {
        const link = this.linkInDocument;
        this.linkInDocument = null;
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
                if (
                    cleanZWChars(link.textContent) === "" &&
                    !link.querySelector("img")
                ) {
                    const [anchorNode, anchorOffset] = rightPos(link);
                    this.dependencies.selection.setSelection(
                        { anchorNode, anchorOffset },
                        { normalize: false },
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
                continue;
            }
            const { color } = anchorEl.style;
            const childNodes = [...anchorEl.childNodes];
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

                const isCursorAtStartOfLink = isZwnbsp(startContainer)
                    ? linkDescendants.indexOf(startContainer) === 0
                    : startContainer.nodeType === Node.TEXT_NODE &&
                      linkDescendants.indexOf(startContainer) === 1 &&
                      startOffset === 0;

                const isCursorAtEndOfLink = isZwnbsp(endContainer)
                    ? linkDescendants.indexOf(endContainer) ===
                      linkDescendants.length - 1
                    : endContainer.nodeType === Node.TEXT_NODE &&
                      linkDescendants.indexOf(endContainer) ===
                          linkDescendants.length - 2 &&
                      endOffset === nodeSize(endContainer);

                if (isCursorAtStartOfLink || isCursorAtEndOfLink) {
                    const [targetNode, targetOffset] = isCursorAtStartOfLink
                        ? leftPos(linkElement)
                        : rightPos(linkElement);
                    this.dependencies.selection.setSelection({
                        anchorNode: targetNode,
                        anchorOffset: isCursorAtStartOfLink
                            ? targetOffset - 1
                            : targetOffset + 1,
                    });
                    return;
                }
            }
        }
        const anchorNode = this.document.getSelection()?.anchorNode;
        const isSelectionInProtected =
            this.document.getSelection()?.isCollapsed &&
            (isProtecting(anchorNode) || isProtected(anchorNode));
        if (!selectionData.currentSelectionIsInEditable || isSelectionInProtected) {
            const popoverEl = document.querySelector(".o-we-linkpopover");
            const anchorNode = document.getSelection()?.anchorNode;
            if (
                (popoverEl && !selectionData.documentSelection) ||
                (anchorNode &&
                    isElement(anchorNode) &&
                    anchorNode.closest(".o-we-linkpopover"))
            ) {
                return;
            }
            this.linkInDocument = null;
            this.closeLinkTools();
        } else if (!selection.isCollapsed) {
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
            const isLinkEditable = this.getResource("is_link_editable_predicates").some(
                (p) => p(closestLinkElement),
            );
            if (closestLinkElement && closestLinkElement.isContentEditable) {
                if (
                    closestLinkElement !== this.linkInDocument ||
                    !this.currentOverlay.isOpen
                ) {
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
     * @param {HTMLLinkElement} linkElement
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

    removeLinkInDocument(link = this.linkInDocument) {
        if (!link.parentElement.isContentEditable || this.isUnremovable(link)) {
            return;
        }
        const cursors = this.dependencies.selection.preserveSelection();
        if (link && link.isContentEditable && link.parentElement.isContentEditable) {
            cursors.update(callbacksForCursorUpdate.unwrap(link));
            unwrapContents(link);
        }
        cursors.restore();
        this.linkInDocument = null;
        this.dependencies.selection.focusEditable();
        this.dependencies.history.addStep();
    }

    removeLinkFromSelectionIsDisabled(selection) {
        for (const node of this.dependencies.selection.getTargetedNodes()) {
            const linkEl = closestElement(node, "a");
            if (
                linkEl &&
                !this.isLinkImmutable(linkEl) &&
                !this.isUnremovable(linkEl)
            ) {
                return false;
            }
        }
        return true;
    }
    removeLinkFromSelection() {
        const selection = this.dependencies.split.splitSelection();

        let { anchorNode, focusNode } = selection;
        let anchorOffset, focusOffset;
        const direction = selection.direction;
        let [startLink, endLink] = [
            closestElement(anchorNode, "a"),
            closestElement(focusNode, "a"),
        ];
        let cursors;
        if (startLink) {
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
        let targetedNodes = this.dependencies.selection.getTargetedNodes();
        const selectedImageNodes = targetedNodes.filter(
            (node) => node.tagName === "IMG",
        );
        if (
            selectedImageNodes.length &&
            startLink &&
            endLink &&
            startLink === endLink
        ) {
            for (const imageNode of selectedImageNodes) {
                let imageLink;
                const figure = closestElement(imageNode, "figure");
                if (direction === DIRECTIONS.RIGHT) {
                    imageLink = this.dependencies.split.splitAroundUntil(
                        figure || imageNode,
                        endLink,
                    );
                } else {
                    imageLink = this.dependencies.split.splitAroundUntil(
                        figure || imageNode,
                        startLink,
                    );
                }
                cursors.update(callbacksForCursorUpdate.unwrap(imageLink));
                unwrapContents(imageLink);
                if (figure && figure.parentElement !== this.editable) {
                    unwrapContents(figure.parentElement);
                }
                [startLink, endLink] = [
                    closestElement(anchorNode, "a"),
                    closestElement(focusNode, "a"),
                ];
            }
            cursors.restore();
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
        if (
            startLink &&
            startLink.isConnected &&
            startLink.parentElement.isContentEditable &&
            !this.isUnremovable(startLink)
        ) {
            anchorNode = this.dependencies.split.splitAroundUntil(
                anchorNode,
                startLink,
            );
            anchorOffset = direction === DIRECTIONS.RIGHT ? 0 : nodeSize(anchorNode);
            this.dependencies.selection.setSelection(
                { anchorNode, anchorOffset, focusNode, focusOffset },
                { normalize: true },
            );
        }
        if (
            endLink &&
            endLink.isConnected &&
            endLink.parentElement.isContentEditable &&
            !this.isUnremovable(endLink)
        ) {
            focusNode = this.dependencies.split.splitAroundUntil(
                focusNode,
                closestElement(focusNode, "a"),
            );
            focusOffset = direction === DIRECTIONS.RIGHT ? nodeSize(focusNode) : 0;
            this.dependencies.selection.setSelection(
                { anchorNode, anchorOffset, focusNode, focusOffset },
                { normalize: true },
            );
        }
        targetedNodes = this.dependencies.selection.getTargetedNodes();
        const links = new Set(
            targetedNodes
                .map((node) => closestElement(node, "a"))
                .filter(
                    (a) =>
                        a &&
                        a.isContentEditable &&
                        a.parentElement.isContentEditable &&
                        !this.isUnremovable(a),
                ),
        );
        if (links.size) {
            for (const link of links) {
                cursors.update(callbacksForCursorUpdate.unwrap(link));
                unwrapContents(link);
            }
            cursors.restore();
        }
        if (startBlock) {
            this.removeEmptyLinks(startBlock);
        }
        if (endBlock && endBlock !== startBlock) {
            this.removeEmptyLinks(endBlock);
        }
        this.dependencies.history.addStep();
    }

    removeEmptyLinks(root) {
        const remove = (node) => {
            for (const child of node.childNodes) {
                remove(child);
            }
            if (!this.isUnremovable(node)) {
                node.before(...node.childNodes);
                node.remove();
            }
        };
        for (const link of root.querySelectorAll("a")) {
            if (
                [...link.childNodes].some(isVisible) ||
                !link.parentElement.isContentEditable ||
                this.isUnremovable(link) ||
                this.getResource("legit_empty_link_predicates").some((p) => p(link))
            ) {
                continue;
            }
            remove(link);
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
                (url === href ||
                    url + "/" === href ||
                    url === deduceURLfromText(href, linkEl))
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
        const selection = this.document.getSelection();
        if (
            ev.inputType === "insertText" &&
            selection.isCollapsed &&
            selection.anchorNode.nodeType === Node.TEXT_NODE &&
            selection.anchorNode.parentElement.tagName === "A"
        ) {
            const offset = selection.anchorOffset;
            selection.collapse(selection.anchorNode, 0);
            selection.collapse(selection.anchorNode, offset);
        }
        this.updateCurrentLinkSyncState();
    }

    onInputDeleteNormalizeLink() {
        const { anchorNode } = this.dependencies.selection.getEditableSelection();
        const linkEl = closestElement(anchorNode, "a");
        if (linkEl && linkEl.isContentEditable) {
            const label = linkEl.innerText;
            const url = deduceURLfromText(label, linkEl);
            if (url && this.isCurrentLinkInSync) {
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
        if (
            imageToDelete.parentElement.tagName === "A" &&
            !this.isUnremovable(imageToDelete.parentElement) &&
            imageToDelete.parentElement.parentElement.isContentEditable
        ) {
            const cursors = this.dependencies.selection.preserveSelection();
            cursors.update(callbacksForCursorUpdate.remove(imageToDelete));
            imageToDelete.remove();
            this.closeLinkTools(cursors);
            this.dependencies.history.addStep();
            return true;
        }
        return false;
    }

    handleAutomaticLinkInsertion() {
        const convertToLink = this.prepareConvertToLink();
        if (convertToLink) {
            return convertToLink();
        }
    }

    /**
     * @returns {Function}
     */
    prepareConvertToLink() {
        let selection = this.dependencies.selection.getEditableSelection();
        if (
            isHtmlContentSupported(selection) &&
            !closestElement(selection.anchorNode, "a") &&
            selection.anchorNode.nodeType === Node.TEXT_NODE
        ) {
            const cursor = this.dependencies.selection.preserveSelection();
            mergeAdjacentTextNodes(selection.anchorNode.parentNode, cursor);
            cursor.restore();
            selection = this.dependencies.selection.getEditableSelection();
            const textSliced = selection.anchorNode.textContent.slice(
                0,
                selection.anchorOffset,
            );
            const textNodeSplitted = textSliced.split(/\s/);
            const potentialUrl = textNodeSplitted.pop();
            const match = [
                ...potentialUrl.matchAll(
                    new RegExp(URL_REGEX.source, URL_REGEX.flags + "g"),
                ),
            ].pop();

            if (match) {
                const nodeForSelectionRestore = selection.anchorNode.splitText(
                    selection.anchorOffset,
                );
                let url;
                if (!EMAIL_REGEX.test(match[0])) {
                    url = match[2] ? match[0] : "https://" + match[0];
                } else {
                    url = "mailto:" + match[0];
                }

                const startOffset =
                    selection.anchorOffset - potentialUrl.length + match.index;
                const text = selection.anchorNode.textContent.slice(
                    startOffset,
                    startOffset + match[0].length,
                );
                const textNodeToReplace = selection.anchorNode.splitText(startOffset);
                textNodeToReplace.splitText(match[0].length);
                const link = this.createLink(url, text);
                return () => {
                    textNodeToReplace.splitText(match[0].length);
                    textNodeToReplace.parentNode.replaceChild(link, textNodeToReplace);
                    if (link.getAttribute("href") === link.textContent) {
                        this.newlyInsertedLinks.add(link);
                    }
                    return nodeForSelectionRestore;
                };
            }
        }
    }

    /**
     * @param {Object} params
     * @param {Element} params.targetNode
     * @param {number} params.targetOffset
     * @param {Element} params.blockToSplit
     */
    handleSplitBlock(params) {
        return this.handleEnterAtEdgeOfLink(
            params,
            this.dependencies.split.splitElementBlock,
        );
    }

    /**
     * @param {Object} params
     * @param {Element} params.targetNode
     * @param {number} params.targetOffset
     */
    handleInsertLineBreak(params) {
        return this.handleEnterAtEdgeOfLink(
            params,
            this.dependencies.lineBreak.insertLineBreakElement,
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
        let { targetNode, targetOffset } = params;
        if (targetNode.tagName !== "A") {
            return;
        }
        const edge = isPositionAtEdgeofLink(targetNode, targetOffset);
        if (!edge) {
            return;
        }
        [targetNode, targetOffset] =
            edge === "start" ? leftPos(targetNode) : rightPos(targetNode);
        const blockToSplit = targetNode;
        splitOrLineBreakCallback({ ...params, targetNode, targetOffset, blockToSplit });
        return true;
    }

    /**
     * @returns {true|undefined}
     */
    handleDeleteBackward({ startContainer, startOffset, endContainer, endOffset }) {
        if (startContainer !== endContainer || startOffset !== 0 || endOffset !== 1) {
            return;
        }
        if (
            startContainer.nodeType !== Node.TEXT_NODE ||
            startContainer.textContent !== "﻿"
        ) {
            return;
        }
        const previousSibling = startContainer.previousSibling;
        if (
            previousSibling?.nodeType !== Node.ELEMENT_NODE ||
            !previousSibling.matches("a.btn")
        ) {
            return;
        }
        this.dependencies.selection.setSelection({
            anchorNode: previousSibling,
            anchorOffset: previousSibling.childNodes.length - 1,
        });
        return true;
    }

    handleAfterInsert(insertedNodes) {
        for (const node of insertedNodes) {
            if (node.nodeType === Node.ELEMENT_NODE) {
                for (const link of selectElements(node, "A")) {
                    if (
                        link.getAttribute("href") === link.textContent &&
                        !this.isImage
                    ) {
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
                    },
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
        return this.getResource("immutable_link_selectors").some((s) =>
            linkEl.matches(s),
        );
    }

    doubleClickLinkOverrides(ev) {
        const clickedLink = closestElement(ev.target, "a");
        if (clickedLink) {
            this.dependencies.selection.modifySelection("extend", "backward", "word");
            this.document.getSelection().collapseToStart();
            this.dependencies.selection.modifySelection("extend", "forward", "word");

            const { anchorNode, focusNode, anchorOffset, focusOffset } =
                this.dependencies.selection.getEditableSelection();

            if (clickedLink.contains(anchorNode) && !clickedLink.contains(focusNode)) {
                this.dependencies.selection.setSelection({
                    anchorNode,
                    anchorOffset,
                    focusNode: clickedLink,
                    focusOffset: nodeSize(clickedLink) - 1,
                });
            } else if (
                !clickedLink.contains(anchorNode) &&
                clickedLink.contains(focusNode)
            ) {
                this.dependencies.selection.setSelection({
                    anchorNode: clickedLink,
                    anchorOffset: 1,
                    focusNode,
                    focusOffset,
                });
            } else if (
                !clickedLink.contains(anchorNode) &&
                !clickedLink.contains(focusNode)
            ) {
                this.dependencies.selection.setSelection({
                    anchorNode: clickedLink,
                    anchorOffset: 1,
                    focusNode: clickedLink,
                    focusOffset: nodeSize(clickedLink) - 1,
                });
            } else {
                this.dependencies.selection.setSelection({
                    anchorNode,
                    anchorOffset,
                    focusNode,
                    focusOffset,
                });
            }

            return true;
        }
    }

    tripleClickButtonOverrides(ev) {
        const selection = this.dependencies.selection.getEditableSelection();
        const buttonElement = isBrowserFirefox()
            ? findInSelection(selection, "a.btn")
            : closestElement(selection.anchorNode, "a.btn");
        if (buttonElement) {
            this.dependencies.selection.setSelection({
                anchorNode: buttonElement,
                anchorOffset: 0,
                focusNode: buttonElement,
                focusOffset: nodeSize(buttonElement),
            });
            ev.preventDefault();
            return true;
        }
    }
}
