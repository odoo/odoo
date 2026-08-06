import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { Plugin } from "@html_editor/plugin";
import { isBlock } from "@html_editor/utils/blocks";
import {
    allowsParagraphRelatedElements,
    isEmptyBlock,
    isParagraphRelatedElement,
    paragraphRelatedElementsSelector,
} from "@html_editor/utils/dom_info";
import { closestElement, descendants, selectElements } from "@html_editor/utils/dom_traversal";
import { withSequence } from "@html_editor/utils/resource";
import { markup } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { renderToElement } from "@web/core/utils/render";

export const SIGNATURE_CLASS = "o-signature-container";
const SIGNATURE_SELECTOR = `.${SIGNATURE_CLASS}`;
const DELIMITER = "--";

export class UserSignaturePlugin extends Plugin {
    static id = "userSignature";
    static dependencies = ["baseContainer", "dom", "history", "selection"];
    static shared = ["cleanSignatures"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "insertUserSignature",
                title: _t("Signature"),
                description: _t("Insert your email signature"),
                icon: "edit_square",
                run: this.insertUserSignature.bind(this),
                isAvailable: (selection) =>
                    isHtmlContentSupported(selection) &&
                    closestElement(selection.anchorNode, allowsParagraphRelatedElements)
                        ?.isContentEditable,
            },
        ],
        powerbox_categories: withSequence(100, { id: "basic_block", name: _t("Basic Block") }),
        powerbox_items: [
            {
                categoryId: "basic_block",
                commandId: "insertUserSignature",
            },
        ],

        /** Predicates */
        is_node_empty_predicates: this.isEmpty.bind(this),
        is_node_splittable_predicates: (node) => {
            if (node.nodeType === Node.ELEMENT_NODE && node.matches(SIGNATURE_SELECTOR)) {
                return false;
            }
        },

        /** Processors */
        normalize_processors: this.normalizeSignatures.bind(this),

        /** Handlers */
        on_selectionchange_handlers: this.handleSelectionInSignature.bind(this),
    };

    cleanSignatures({ rootClone }) {
        for (const el of rootClone.querySelectorAll(SIGNATURE_SELECTOR)) {
            el.remove();
        }
    }

    async insertUserSignature() {
        const [currentUser] = await this.services.orm.read(
            "res.users",
            [user.userId],
            ["signature"]
        );
        if (currentUser && currentUser.signature) {
            const signature = markup(currentUser.signature);
            const signatureBlock = renderToElement("html_editor.Signature", {
                signature: markup`-- <br>${signature}`,
                signatureClass: SIGNATURE_CLASS,
            });
            this.dependencies.dom.insert(signatureBlock);
            const lastPhrasingElement = [
                ...signatureBlock.querySelectorAll(paragraphRelatedElementsSelector),
            ].at(-1);
            if (lastPhrasingElement) {
                this.dependencies.selection.setCursorEnd(lastPhrasingElement);
            } else {
                this.dependencies.selection.setCursorEnd(signatureBlock);
            }
            this.dependencies.history.commit();
        }
    }

    isEmpty(element) {
        if (
            element.nodeType === Node.ELEMENT_NODE &&
            element.matches(SIGNATURE_SELECTOR) &&
            isEmptyBlock(element)
        ) {
            return true;
        }
    }

    /**
     * Find the text node a signature opens with.
     *
     * @param {HTMLElement} signatureEl
     * @returns {Text|undefined} the first text node starting with the delimiter, if any
     */
    getDelimiterNode(signatureEl) {
        return descendants(signatureEl).find(
            (node) =>
                node.nodeType === Node.TEXT_NODE &&
                node.textContent.trimStart().startsWith(DELIMITER)
        );
    }

    /**
     * Rebuild the structure of every signature under `root`: the container
     * opens with a block holding the "-- " delimiter and its line break, and
     * the signature itself follows in a block of its own.
     * @param {HTMLElement} root
     */
    normalizeSignatures(root) {
        const searchRoot = closestElement(root, SIGNATURE_SELECTOR) || root;
        for (const signatureEl of selectElements(searchRoot, SIGNATURE_SELECTOR)) {
            const delimiterNode = this.getDelimiterNode(signatureEl);
            // Without a delimiter there is no signature left to rebuild.
            if (!delimiterNode) {
                continue;
            }
            // Move out whatever sits above the delimiter, one child at a time, until the container starts with it.
            while (signatureEl.parentElement && !signatureEl.firstChild.contains(delimiterNode)) {
                signatureEl.before(signatureEl.firstChild);
            }
            // Split the text node after the delimiter, so it holds nothing else.
            const text = delimiterNode.textContent;
            let delimiterEnd = text.indexOf(DELIMITER) + DELIMITER.length;
            if (text[delimiterEnd] === " ") {
                delimiterEnd += 1;
            }
            if (delimiterEnd < text.length) {
                delimiterNode.splitText(delimiterEnd);
            }
            // The delimiter is always followed by a line break.
            if (delimiterNode.nextSibling?.nodeName !== "BR") {
                delimiterNode.after(this.document.createElement("br"));
            }
            // Inline content following the line break is the signature body: give it a block of its own.
            const brEl = delimiterNode.nextSibling;
            if (brEl.nextSibling && !isBlock(brEl.nextSibling)) {
                const bodyEl = this.dependencies.baseContainer.createBaseContainer();
                brEl.after(bodyEl);
                bodyEl.replaceChildren();
                while (bodyEl.nextSibling && !isBlock(bodyEl.nextSibling)) {
                    bodyEl.append(bodyEl.nextSibling);
                }
                // The content left the delimiter, so the cursor follows it.
                if (this.editable.contains(bodyEl)) {
                    this.dependencies.selection.setCursorEnd(bodyEl);
                }
            }
            // Wrap the delimiter and its line break in a block when they sit directly in the container.
            if (delimiterNode.parentElement === signatureEl) {
                const blockEl = this.dependencies.baseContainer.createBaseContainer();
                delimiterNode.before(blockEl);
                // A new base container comes with a placeholder line break.
                blockEl.replaceChildren(delimiterNode, delimiterNode.nextSibling);
            }
        }
        return root;
    }

    /**
     * Move the cursor to the block above the container whenever it lands on
     * the delimiter. A cursor past the delimiter is in the signature itself
     * and stays where it is.
     *
     * @param {import("@html_editor/core/selection_plugin").SelectionData} selectionData
     */
    handleSelectionInSignature(selectionData) {
        if (!selectionData.documentSelectionIsInEditable) {
            return;
        }
        const { anchorNode, anchorOffset } = selectionData.editableSelection;
        const signatureEl = closestElement(anchorNode, SIGNATURE_SELECTOR);
        // Nothing to move outside a signature, or in a container with no delimiter to sit on.
        if (!signatureEl || !this.getDelimiterNode(signatureEl)) {
            return;
        }
        const range = this.document.createRange();
        range.setStart(signatureEl, 0);
        range.setEnd(anchorNode, anchorOffset);
        if (range.toString().includes(DELIMITER)) {
            return;
        }
        const previousEl = signatureEl.previousElementSibling;
        if (previousEl && isParagraphRelatedElement(previousEl)) {
            this.dependencies.selection.setCursorEnd(previousEl);
        }
    }
}
