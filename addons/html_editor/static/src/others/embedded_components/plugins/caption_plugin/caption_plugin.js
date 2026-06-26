import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { closestBlock, isBlock } from "@html_editor/utils/blocks";
import { renderToElement } from "@web/core/utils/render";
import { unwrapContents } from "@html_editor/utils/dom";
import { closestElement } from "@html_editor/utils/dom_traversal";
import {
    EDITABLE_MEDIA_CLASS,
    isEmptyBlock,
    isParagraphRelatedElement,
    isVisible,
} from "@html_editor/utils/dom_info";
import { boundariesOut, rightPos } from "@html_editor/utils/position";
import { findInSelection } from "@html_editor/utils/selection";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { withSequence } from "@html_editor/utils/resource";
import { DISABLED_NAMESPACE } from "@html_editor/main/toolbar/toolbar_plugin";

const CAPTION_SPAN_SELECTOR = "span.o_caption_editable";

export class CaptionPlugin extends Plugin {
    static id = "caption";
    static dependencies = ["image", "split", "history", "selection", "baseContainer", "clipboard"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "toggleImageCaption",
                title: _t("Add/remove a caption"),
                run: this.toggleImageCaption.bind(this),
                isAvailable: isHtmlContentSupported,
            },
        ],
        toolbar_items: [
            {
                id: "image_caption",
                description: _t("Add/remove a caption"),
                groupId: "image_description",
                commandId: "toggleImageCaption",
                text: _t("Caption"),
                isActive: () => this.hasImageCaption(this.dependencies.image.getTargetedImage()),
            },
        ],
        clean_for_save_handlers: this.cleanForSave.bind(this),
        delete_handlers: this.afterDelete.bind(this),
        beforeinput_handlers: withSequence(-1, this.onBeforeInput.bind(this)),
        before_cut_handlers: this.expandSelectionToCaption.bind(this),
        before_drag_handlers: this.expandSelectionToCaption.bind(this),
        delete_image_overrides: this.handleDeleteImage.bind(this),
        after_save_media_dialog_handlers: this.onImageReplaced.bind(this),
        hints: [{ selector: "FIGCAPTION > .o_caption_editable", text: _t("Write a caption...") }],
        hint_targets_providers: (selectionData) => {
            const captionSpan = closestElement(
                selectionData.editableSelection.anchorNode,
                CAPTION_SPAN_SELECTOR
            );
            if (captionSpan) {
                return [captionSpan];
            }
            return [];
        },
        is_formattable_node_predicates: (node) => {
            if (closestElement(node, CAPTION_SPAN_SELECTOR)) {
                return false;
            }
        },
        unsplittable_node_predicates: [
            (node) => ["FIGURE", "FIGCAPTION"].includes(node.nodeName), // avoid merge
        ],
        image_name_predicates: [this.getImageName.bind(this)],
        link_compatible_selection_predicates: this.isLinkAllowedOnSelection.bind(this),
        toolbar_namespace_providers: withSequence(70, (targetedNodes) => {
            if (
                targetedNodes.length &&
                targetedNodes.every((node) => closestElement(node, CAPTION_SPAN_SELECTOR))
            ) {
                return DISABLED_NAMESPACE;
            }
        }),
        html_drop_overrides: this.onPaste.bind(this),
        paste_overrides: this.onPaste.bind(this),
        normalize_handlers: (root) => {
            let figures = [];
            if (root.matches(CAPTION_SPAN_SELECTOR)) {
                figures = [closestElement(root, "figure")];
            } else {
                figures = [...root.querySelectorAll("figure")];
            }
            figures.forEach((figure) => {
                const captionSpan = figure.querySelector(CAPTION_SPAN_SELECTOR);
                const image = figure.querySelector("IMG");
                if (image && image.getAttribute("data-caption") !== captionSpan.textContent) {
                    image.setAttribute("data-caption", captionSpan.textContent);
                }
                if (captionSpan.textContent) {
                    const figcaption = figure.querySelector("figcaption");
                    figcaption.setAttribute("placeholder", captionSpan.textContent);
                }
            });
        },
        powerbox_blacklist_selectors: CAPTION_SPAN_SELECTOR,
        are_inlines_allowed_at_root_predicates: (node) => node.matches(CAPTION_SPAN_SELECTOR),
        // Consider a <figure> element as empty if it only contains a
        // <figcaption> element (e.g. when its image has just been
        // removed).
        empty_node_predicates: (el) =>
            el.matches?.("figure") &&
            el.children.length === 1 &&
            el.children[0].matches("figcaption"),
        move_node_whitelist_selectors: "figure",

        /** Processors */
        clipboard_content_processors: this.processContentForClipboard.bind(this),
    };

    setup() {
        for (const figure of this.editable.querySelectorAll("figure")) {
            const image = figure.querySelector("img");
            figure.before(image);
            const caption = figure.querySelector("figcaption")?.textContent;
            figure.remove();
            this.addImageCaption(image, caption, false);
            this.dependencies.history.addStep();
        }
    }

    onPaste(selection, clipboardData) {
        const captionSpan = closestElement(selection.anchorNode, CAPTION_SPAN_SELECTOR);
        if (captionSpan) {
            const pastedTextContent = clipboardData.getData("text/plain");
            this.dependencies.clipboard.pasteText(pastedTextContent.replace(/\r?\n|\r/g, ""));
            return true;
        }
    }

    onBeforeInput(ev) {
        if (
            closestElement(ev.target, CAPTION_SPAN_SELECTOR) &&
            ev.inputType === "insertParagraph"
        ) {
            ev.preventDefault();
            const figure = closestElement(ev.target, "figure");
            let nextBlock = figure.nextElementSibling;
            if (
                nextBlock &&
                (!this.dependencies.baseContainer.isCandidateForBaseContainer(nextBlock) ||
                    !isEmptyBlock(nextBlock))
            ) {
                nextBlock = this.dependencies.baseContainer.createBaseContainer("DIV");
                nextBlock.append(this.document.createElement("br"));
                figure.after(nextBlock);
            }
            this.dependencies.selection.setCursorStart(nextBlock);
            this.dependencies.history.addStep();
        }
    }

    getCaptionId() {
        return "" + Math.floor(Math.random() * Date.now());
    }

    hasImageCaption(image) {
        if (!image) {
            return;
        }
        const block = closestBlock(image.parentElement);
        return block.nodeName === "FIGURE" && !!block.querySelector(CAPTION_SPAN_SELECTOR);
    }

    toggleImageCaption(image = this.dependencies.image.getTargetedImage()) {
        if (!image) {
            return;
        }
        if (this.hasImageCaption(image)) {
            this.removeImageCaption(image);
        } else {
            this.addImageCaption(image, image.getAttribute("data-caption") || "");
            this.dependencies.history.addStep();
        }
    }

    addImageCaption(image, captionText = "") {
        // Move the image within a figure element.
        const figure = this.document.createElement("figure");
        const link = image.parentElement.nodeName === "A" && image.parentElement;
        const target = link || image;
        const blockEl = closestBlock(target.parentElement);
        if ((target.nextSibling || target.previousSibling) && isParagraphRelatedElement(blockEl)) {
            // <p>wx<a><img/></a>yz</p> => <p>wx</p><p><a><img/></a></p><p>yz</p>
            // <p>wx<img/>yz</p> => <p>wx</p><p><img/></p><p>yz</p>
            const block = this.dependencies.split.splitAroundUntil(target, blockEl);
            if (isBlock(block.previousSibling) && !isVisible(block.previousSibling)) {
                block.previousSibling.remove();
            }
            if (isBlock(block.nextSibling) && !isVisible(block.nextSibling)) {
                block.nextSibling.remove();
            }
        }
        // => <p><figure><img/></figure></p>
        // or <p><a><figure><img/></figure></a></p>
        image.before(figure);
        figure.append(image);
        if (!link && isParagraphRelatedElement(figure.parentElement)) {
            // => <figure><img/></figure></p>
            // but still <p><a><figure><img/></figure></p>
            unwrapContents(figure.parentElement);
        }
        // Set the caption and its ID.
        const captionId = this.getCaptionId();
        image.setAttribute("data-caption-id", captionId);
        image.setAttribute("data-caption", captionText || "");
        figure.setAttribute("contenteditable", "false");
        image.classList.add(EDITABLE_MEDIA_CLASS);
        const figcaptionEl = renderToElement("html_editor.EmbeddedCaptionBlueprint", {
            captionId,
        });
        figure.append(figcaptionEl);
        this.setupCaption(figcaptionEl, image);
    }

    /**
     * Initialize a figcaption
     * @param {HTMLElement} figcaption
     * @param {HTMLImageElement} image
     */
    setupCaption(figcaption, image) {
        const span = figcaption.querySelector(CAPTION_SPAN_SELECTOR);
        if (span) {
            const captionText = image.getAttribute("data-caption") || "";
            if (captionText) {
                span.textContent = captionText;
                figcaption.setAttribute("placeholder", captionText);
            }
            this.dependencies.selection.setCursorEnd(span);
        }
    }

    removeImageCaption(image) {
        const figure = closestElement(image, "figure");
        if (figure) {
            figure.querySelector("figcaption").remove();
            if (!isParagraphRelatedElement(closestBlock(figure.parentElement))) {
                const baseContainer = this.dependencies.baseContainer.createBaseContainer();
                if (figure.parentElement.nodeName === "A") {
                    figure.parentElement.before(baseContainer);
                    baseContainer.append(figure.parentElement);
                } else {
                    figure.before(baseContainer);
                    baseContainer.append(figure);
                }
            }
            unwrapContents(figure);
            image.removeAttribute("data-caption-id"); // (keep the data-caption for if we toggle again)
            image.classList.remove(EDITABLE_MEDIA_CLASS);

            const [anchorNode, anchorOffset, focusNode, focusOffset] = boundariesOut(image);
            this.dependencies.selection.setSelection({
                anchorNode,
                anchorOffset,
                focusNode,
                focusOffset,
            });
            this.dependencies.history.addStep();
        }
    }

    cleanForSave({ root }) {
        for (const figure of root.querySelectorAll("figure")) {
            figure.removeAttribute("contenteditable");
            const image = figure.querySelector("img");
            const span = figure.querySelector(CAPTION_SPAN_SELECTOR);
            const captionText = span?.textContent || image.getAttribute("data-caption") || "";
            figure.querySelector("figcaption").remove();
            const newFigcaption = root.ownerDocument.createElement("figcaption");
            newFigcaption.textContent = captionText;
            image.removeAttribute("data-caption");
            image.removeAttribute("data-caption-id");
            image.classList.remove(EDITABLE_MEDIA_CLASS);
            image.after(newFigcaption);
        }
    }

    getImageName(image) {
        if (closestElement(image, "figure")) {
            return image.getAttribute("data-caption");
        }
    }

    isLinkAllowedOnSelection() {
        const figure = findInSelection(
            this.dependencies.selection.getSelectionData().deepEditableSelection,
            "figure"
        );
        if (
            figure &&
            this.dependencies.selection
                .getTargetedNodes()
                .every((node) => closestElement(node, "figure") === figure)
        ) {
            return true;
        }
    }

    onImageReplaced(media) {
        const figure = closestElement(media, "figure");
        let anchorNode, anchorOffset;
        if (figure) {
            if (media.nodeName === "IMG") {
                [anchorNode, anchorOffset] = rightPos(figure);
                const span = figure.querySelector(CAPTION_SPAN_SELECTOR);
                const caption = span?.textContent || "";
                figure.before(media);
                figure.remove();
                this.addImageCaption(media, caption, false);
            } else {
                this.removeImageCaption(media);
                [anchorNode, anchorOffset] = rightPos(media);
            }
            this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
        }
    }

    afterDelete() {
        const { anchorNode } = this.dependencies.selection.getEditableSelection();
        const targetedNodes = this.dependencies.selection.getTargetedNodes();
        for (const figure of this.editable.querySelectorAll("figure:not(:has(img))")) {
            const isSelectionInFigure =
                targetedNodes.some((node) => figure.contains(node)) || anchorNode === figure;
            const sibling = figure.nextSibling || figure.previousSibling;
            figure.remove();
            if (isSelectionInFigure) {
                // Note: this assumes the selection is collapsed after delete.
                this.dependencies.selection.setSelection({
                    anchorNode: sibling,
                    anchorOffset: 0,
                });
            }
        }
    }

    handleDeleteImage(image) {
        const figure = closestElement(image, "figure");
        if (figure) {
            const sibling = figure.nextSibling || figure.previousSibling;
            figure.remove();
            this.dependencies.selection.setSelection({
                anchorNode: sibling,
                anchorOffset: 0,
            });
            this.dependencies.history.addStep();
            return true;
        }
    }

    expandSelectionToCaption(selection) {
        const startFigure = closestElement(selection.anchorNode, "figure");
        const endFigure = closestElement(selection.focusNode, "figure");

        if (startFigure && startFigure === endFigure) {
            const [anchorNode, anchorOffset, focusNode, focusOffset] = boundariesOut(startFigure);
            this.dependencies.selection.setSelection(
                { anchorNode, anchorOffset, focusNode, focusOffset },
                { normalize: false }
            );
        }
    }

    /**
     * @param {DocumentFragment} clonedContents
     * @param {import("@html_editor/core/selection_plugin").EditorSelection} selection
     */
    processContentForClipboard(clonedContents, selection) {
        if (clonedContents.firstChild.nodeName === "IMG") {
            clonedContents = selection.commonAncestorContainer.cloneNode(true);
        }
        return clonedContents;
    }
}
