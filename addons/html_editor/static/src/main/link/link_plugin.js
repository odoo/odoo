import { Plugin } from "@html_editor/plugin";
import { unwrapContents } from "@html_editor/utils/dom";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { findInSelection, callbacksForCursorUpdate } from "@html_editor/utils/selection";
import { _t } from "@web/core/l10n/translation";
import { LinkPopover } from "./link_popover";
import { EMAIL_REGEX, URL_REGEX, deduceURLfromText } from "./utils";
import { DIRECTIONS, nodeSize } from "@html_editor/utils/position";

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

export class LinkPlugin extends Plugin {
    static name = "link";
    static dependencies = ["dom", "selection", "split", "overlay"];
    // @phoenix @todo: do we want to have createLink and insertLink methods in link plugin?
    static shared = ["createLink", "insertLink", "getPathAsUrlCommand"];
    /** @type { (p: LinkPlugin) => Record<string, any> } */
    static resources = (p) => ({
        toolbarGroup: {
            id: "link",
            sequence: 40,
            buttons: [
                {
                    id: "link",
                    cmd: "CREATE_LINK_ON_SELECTION",
                    icon: "fa-link",
                    name: "link",
                    label: _t("Link"),
                    isFormatApplied: isLinkActive,
                },
                {
                    id: "unlink",
                    cmd: "REMOVE_LINK_FROM_SELECTION",
                    icon: "fa-unlink",
                    name: "unlink",
                    label: _t("Remove Link"),
                },
            ],
        },
        powerboxCategory: { id: "navigation", name: _t("Navigation"), sequence: 40 },
        powerboxCommands: [
            {
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
        onSelectionChange: p.handleSelectionChange.bind(p),
    });
    setup() {
        this.overlay = this.shared.createOverlay(LinkPopover, { position: "bottom-start" });
        this.addDomListener(this.editable, "click", (ev) => {
            if (ev.target.tagName === "A") {
                ev.preventDefault();
                this.toggleLinkTools({ link: ev.target });
            }
        });
        this.addDomListener(this.editable, "keydown", (ev) => {
            if (ev.key === "Enter" || ev.key === " ") {
                this.handleAutomaticLinkInsertion();
            }
        });
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
                this.normalizeLink(payload.node);
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
        const link = this.createLink(url, label);
        this.shared.domInsert(link);
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

    normalizeLink(node) {
        const linkEl = closestElement(node, "a");
        if (linkEl && linkEl.isContentEditable) {
            const label = linkEl.innerText;
            const url = deduceURLfromText(label, linkEl);
            if (url) {
                linkEl.setAttribute("href", url);
            }
        }
    }

    handleSelectionChange(selection) {
        if (!selection.isCollapsed) {
            this.overlay.close();
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

            const props = {
                linkEl,
                onApply: (url, label) => {
                    this.linkElement.href = url;
                    if (this.linkElement.innerText === label) {
                        this.overlay.close();
                        this.shared.setSelection(this.shared.getEditableSelection());
                    } else {
                        this.linkElement.innerText = label;
                        this.overlay.close();
                        this.shared.setCursorEnd(this.linkElement);
                    }
                    this.dispatch("ADD_STEP");
                    this.removeCurrentLinkIfEmtpy();
                },
                onRemove: () => {
                    this.removeLink();
                    this.overlay.close();
                    this.dispatch("ADD_STEP");
                },
                onCopy: () => {
                    this.overlay.close();
                },
            };
            // pass the link element to overlay to prevent position change
            this.overlay.open({ target: this.linkElement, props });
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
            return linkElement;
        } else {
            // create a new link element
            const link = this.document.createElement("a");
            if (selection.isCollapsed) {
                // todo: handle this case
            } else {
                const content = this.shared.extractContent(selection);
                link.append(content);
            }
            this.shared.domInsert(link);
            this.shared.setCursorEnd(link);
            this.dispatch("ADD_STEP");
            return link;
        }
    }

    removeCurrentLinkIfEmtpy() {
        if (this.linkElement && this.linkElement.innerText === "") {
            this.linkElement.remove();
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
    }

    removeLinkFromSelection() {
        const selection = this.shared.splitSelection();
        const cursors = this.shared.preserveSelection();

        // If not, unlink only the part(s) of the link(s) that are selected:
        // `<a>a[b</a>c<a>d</a>e<a>f]g</a>` => `<a>a</a>[bcdef]<a>g</a>`.
        let { anchorNode, focusNode, anchorOffset, focusOffset } = selection;
        const direction = selection.direction;
        // Split the links around the selection.
        const [startLink, endLink] = [
            closestElement(anchorNode, "a"),
            closestElement(focusNode, "a"),
        ];
        if (startLink) {
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

    /**
     * Inserts a link in the editor. Called after pressing space or (shif +) enter.
     * Performs a regex check to determine if the url has correct syntax.
     */
    handleAutomaticLinkInsertion() {
        let selection = this.shared.getEditableSelection();
        if (
            isHtmlContentSupported(selection.anchorNode) &&
            !closestElement(selection.anchorNode).closest("a") &&
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
            }
        }
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
