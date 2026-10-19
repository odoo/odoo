import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { Plugin } from "@html_editor/plugin";
import { baseContainerGlobalSelector } from "@html_editor/utils/base_container";
import { unwrapContents } from "@html_editor/utils/dom";
import {
    allowsParagraphRelatedElements,
    isEmptyBlock,
    paragraphRelatedElementsSelector,
} from "@html_editor/utils/dom_info";
import { childNodes, closestElement, selectElements } from "@html_editor/utils/dom_traversal";
import { withSequence } from "@html_editor/utils/resource";
import { markup } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { renderToElement } from "@web/core/utils/render";

export const SIGNATURE_CLASS = "o-signature-container";
const QUOTE_CONTAINER_ATTRIBUTE = "data-o-mail-quote-container";
const QUOTE_ATTRIBUTE = "data-o-mail-quote";
const SIGNATURE_SELECTOR = `.${SIGNATURE_CLASS}`;
const QUOTE_CONTAINER_SELECTOR = `[${QUOTE_CONTAINER_ATTRIBUTE}='1']`;
const QUOTE_SELECTOR = `[${QUOTE_ATTRIBUTE}='1']`;
const DELIMITER_TEXT_CONTENT = "-- ";

/**
 * @typedef {Object} SignatureStructureReport
 * @property {boolean} isRecoverable
 * @property {boolean} isValid
 * @property {Node[]} delimiters
 * @property {Node[]} content
 * @property {Element} signatureEl
 * @property {Element|undefined} quoteWrapperEl
 * @property {Element|undefined} contentWrapperEl
 */

export class UserSignaturePlugin extends Plugin {
    static id = "userSignature";
    static dependencies = ["baseContainer", "contentEditablePlugin", "dom", "history", "selection"];
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

        delete_backward_overrides: this.handleDeleteBackward.bind(this),

        /** Predicates */
        is_node_splittable_predicates: (node) => {
            if (node.nodeType === Node.ELEMENT_NODE && node.matches(SIGNATURE_SELECTOR)) {
                return false;
            }
        },

        /** Processors */
        clean_for_save_processors: (root) => this.cleanForSave(root),
        normalize_processors: this.normalizeSignatures.bind(this),
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
                signature,
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

    handleDeleteBackward({ endContainer }) {
        const signatureEl = closestElement(endContainer, SIGNATURE_SELECTOR);
        if (!signatureEl) {
            return;
        }
        const signatureReport = this.validateSignatureStructure(signatureEl);
        if (!signatureReport.isValid || !isEmptyBlock(signatureReport.contentWrapperEl)) {
            return;
        }
        const cursors = this.dependencies.selection.preserveSelection();
        signatureEl.before(...signatureReport.content);
        signatureEl.remove();
        cursors.restore();
        return true;
    }

    ensureSignatureElAttributes(signatureEl) {
        if (!signatureEl.matches("[contenteditable='false']")) {
            signatureEl.setAttribute("contenteditable", "false");
        }
        if (!signatureEl.matches(QUOTE_CONTAINER_SELECTOR)) {
            signatureEl.setAttribute(QUOTE_CONTAINER_ATTRIBUTE, "1");
        }
    }

    ensureQuoteWrapperElAttributes(quoteWrapperEl) {
        if (!quoteWrapperEl.matches(QUOTE_SELECTOR)) {
            quoteWrapperEl.setAttribute(QUOTE_ATTRIBUTE, "1");
        }
    }

    ensureContentWrapperElAttributes(contentWrapperEl) {
        if (!contentWrapperEl.matches("[contenteditable='true']")) {
            contentWrapperEl.setAttribute("contenteditable", "true");
        }
    }

    ensureSignatureAttributes({ signatureEl, quoteWrapperEl, contentWrapperEl }) {
        this.ensureContentWrapperElAttributes(contentWrapperEl);
        this.ensureQuoteWrapperElAttributes(quoteWrapperEl);
        this.ensureSignatureElAttributes(signatureEl);
    }

    ensureSignatureContent({ contentWrapperEl }) {
        this.dependencies.dom.wrapInlinesInBlocks(contentWrapperEl, {
            baseContainerNodeName: this.dependencies.baseContainer.getDefaultNodeName(),
            cursors: this.dependencies.selection.preserveSelection(),
        });
        if (!contentWrapperEl.firstElementChild) {
            contentWrapperEl.append(this.dependencies.baseContainer.createBaseContainer());
        }
    }

    /**
     * Validates how closely a signature element matches the expected DOM
     * structure during edition:
     *     signatureEl
     *       └─ quoteWrapperEl
     *            ├─ delimiter text node
     *            ├─ <br>
     *            └─ contentWrapperEl
     *                 └─ signature content
     *
     * Returns a validation report describing the provided signature structure.
     * - `content` contains nodes considered to be signature content at the
     *   deepest successfully validated structural level.
     * - `delimiters` contains the delimiter text node and its `<br>` when both
     *   were found, and is empty otherwise.
     * - `isRecoverable` indicates that the root signature container itself is
     *   valid, meaning the element can potentially be normalized or
     *   reconstructed.
     * - `isValid` indicates that the complete expected signature structure was
     *   found.
     *
     * @param {Element} signatureEl
     *     The element expected to represent a signature container.
     * @returns {SignatureStructureReport}
     */
    validateSignatureStructure(signatureEl) {
        const report = {
            isRecoverable: false,
            isValid: false,
            delimiters: [],
            content: [],
            signatureEl,
            quoteWrapperEl: undefined,
            contentWrapperEl: undefined,
        };
        const isContainerValid =
            signatureEl?.nodeType === Node.ELEMENT_NODE &&
            signatureEl.matches(`div${SIGNATURE_SELECTOR}`);
        if (!isContainerValid) {
            return report;
        }
        report.isRecoverable = true;
        report.content = childNodes(signatureEl);
        const quoteWrapperEl = report.content.length === 1 && signatureEl.firstElementChild;
        const isQuoteWrapperValid =
            quoteWrapperEl && quoteWrapperEl.matches(`div:not(${baseContainerGlobalSelector})`);
        if (!isQuoteWrapperValid) {
            return report;
        }
        report.quoteWrapperEl = quoteWrapperEl;
        report.content = childNodes(quoteWrapperEl);
        const delimiterTextNode = quoteWrapperEl.firstChild;
        const delimiterBR = delimiterTextNode?.nextSibling;
        const isDelimiterValid =
            delimiterTextNode?.textContent === DELIMITER_TEXT_CONTENT &&
            delimiterBR?.nodeName === "BR";
        if (!isDelimiterValid) {
            return report;
        }
        report.delimiters = [delimiterTextNode, delimiterBR];
        const delimiterSiblings = [];
        let currentNode = delimiterBR.nextSibling;
        while (currentNode) {
            delimiterSiblings.push(currentNode);
            currentNode = currentNode.nextSibling;
        }
        report.content = delimiterSiblings;
        const isContentWrapperValid =
            delimiterSiblings.length === 1 &&
            delimiterSiblings[0].nodeType === Node.ELEMENT_NODE &&
            !this.dependencies.baseContainer.isCandidateForBaseContainer(delimiterSiblings[0]);
        if (!isContentWrapperValid) {
            return report;
        }
        report.contentWrapperEl = delimiterSiblings[0];
        report.content = childNodes(report.contentWrapperEl);
        report.isValid = true;
        return report;
    }

    /**
     * Repairs a recoverable signature structure so that it matches the expected
     * DOM structure validated by @see validateSignatureStructure
     *
     * The provided report is updated in place according to changes.
     *
     * @param {SignatureStructureReport} report
     * @returns {void}
     */
    fixSignatureStructure(report) {
        if (!report.isRecoverable) {
            return;
        }
        const cursors = this.dependencies.selection.preserveSelection();
        if (!report.quoteWrapperEl) {
            const quoteWrapperEl = this.document.createElement("DIV");
            report.signatureEl.replaceChildren(quoteWrapperEl);
            report.quoteWrapperEl = quoteWrapperEl;
        }
        if (!report.contentWrapperEl) {
            report.delimiters = [];
            const contentWrapperEl = this.document.createElement("DIV");
            report.quoteWrapperEl.replaceChildren(contentWrapperEl);
            contentWrapperEl.append(...report.content);
            report.contentWrapperEl = contentWrapperEl;
        }
        if (report.delimiters.length === 0) {
            const delimiterTextNode = this.document.createTextNode(`${DELIMITER_TEXT_CONTENT}`);
            const br = this.document.createElement("BR");
            report.quoteWrapperEl.prepend(delimiterTextNode, br);
            report.delimiters = [delimiterTextNode, br];
        }
        report.isValid = true;
        cursors.restore();
    }

    normalizeSignatures(root) {
        for (const signatureEl of selectElements(root, SIGNATURE_SELECTOR)) {
            const signatureReport = this.validateSignatureStructure(signatureEl);
            if (!signatureReport.isRecoverable) {
                signatureEl.remove();
                continue;
            } else if (!signatureReport.isValid) {
                this.fixSignatureStructure(signatureReport);
            }
            this.ensureSignatureAttributes(signatureReport);
            this.ensureSignatureContent(signatureReport);
        }
        return root;
    }

    cleanForSave(root) {
        for (const signatureEl of selectElements(root, SIGNATURE_SELECTOR)) {
            const signatureReport = this.validateSignatureStructure(signatureEl);
            if (signatureReport.isValid) {
                signatureReport.signatureEl.removeAttribute("contenteditable");
                unwrapContents(signatureReport.contentWrapperEl);
            }
            const nextElementSibling = signatureEl.nextElementSibling;
            if (
                nextElementSibling &&
                !nextElementSibling.nextElementSibling &&
                isEmptyBlock(nextElementSibling) &&
                this.dependencies.baseContainer.isCandidateForBaseContainer(nextElementSibling)
            ) {
                nextElementSibling.remove();
            }
        }
        return root;
    }
}
