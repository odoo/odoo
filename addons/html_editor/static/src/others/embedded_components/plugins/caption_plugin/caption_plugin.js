import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { closestBlock, isBlock } from "@html_editor/utils/blocks";
import { renderToElement } from "@web/core/utils/render";
import { unwrapContents } from "@html_editor/utils/dom";
import { closestElement } from "@html_editor/utils/dom_traversal";
import {
    EDITABLE_MEDIA_CLASS,
    isParagraphRelatedElement,
    isVisible,
} from "@html_editor/utils/dom_info";
import { boundariesOut, rightPos } from "@html_editor/utils/position";
import { findInSelection } from "@html_editor/utils/selection";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";

export class CaptionPlugin extends Plugin {
    static id = "caption";
    static dependencies = [
        "image",
        "split",
        "history",
        "embeddedComponents",
        "selection",
        "baseContainer",
    ];
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
                text: "Caption",
                isActive: () => this.hasImageCaption(this.dependencies.image.getTargetedImage()),
            },
        ],
        clean_for_save_handlers: this.cleanForSave.bind(this),
        mount_component_handlers: this.setupNewCaption.bind(this),
        delete_handlers: this.afterDelete.bind(this),
        before_cut_handlers: this.expandSelectionToCaption.bind(this),
        before_drag_handlers: this.expandSelectionToCaption.bind(this),
        delete_image_overrides: this.handleDeleteImage.bind(this),
        after_save_media_dialog_handlers: this.onImageReplaced.bind(this),
        hints: [{ selector: "FIGCAPTION", text: _t("Write a caption...") }],
        unsplittable_node_predicates: [
            (node) => ["FIGURE", "FIGCAPTION"].includes(node.nodeName), // avoid merge
        ],
        image_name_predicates: [this.getImageName.bind(this)],
        link_compatible_selection_predicates: [this.isLinkAllowedOnSelection.bind(this)],
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
            // Embed the captions.
            const image = figure.querySelector("img");
            figure.before(image);
            const caption = figure.querySelector("figcaption")?.textContent;
            figure.remove();
            this.addImageCaption(image, caption, false);
        }
    }

    cleanForSave({ root }) {
        for (const figure of root.querySelectorAll("figure")) {
            figure.removeAttribute("contenteditable");
            const image = figure.querySelector("img");
            // Remove embedding and convert caption attribute to text.
            figure.querySelector("figcaption").remove();
            const caption = root.ownerDocument.createElement("figcaption");
            caption.textContent = image.getAttribute("data-caption");
            image.removeAttribute("data-caption");
            image.removeAttribute("data-caption-id");
            image.classList.remove(EDITABLE_MEDIA_CLASS);
            image.after(caption);
        }
    }

    hasImageCaption(image) {
        if (!image) {
            return;
        }
        const block = closestBlock(image);
        return (
            block.nodeName === "FIGURE" && !!block.querySelector("[data-embedded='caption'] input")
        );
    }

    toggleImageCaption(image = this.dependencies.image.getTargetedImage()) {
        if (!image) {
            return;
        }
        if (this.hasImageCaption(image)) {
            this.removeImageCaption(image);
        } else {
            this.addImageCaption(image, image.getAttribute("data-caption") || "");
        }
    }

    getCaptionId() {
        return "" + Math.floor(Math.random() * Date.now());
    }

    addImageCaption(image, captionText = "", focusInput = true) {
        this.captionsBeingAdded ||= new Set();
        // Move the image within a figure element.
        const figure = this.document.createElement("figure");
        const link = image.parentElement.nodeName === "A" && image.parentElement;
        if (link && (link.previousSibling || link.nextSibling)) {
            // <p>wx<a><img/></a>yz</p> => <p>wx</p><p><a><img/></a></p><p>yz</p>
            this.dependencies.split.splitAroundUntil(link, closestBlock(link));
        } else if (
            !link &&
            (image.previousSibling || image.nextSibling) &&
            isParagraphRelatedElement(closestBlock(image))
        ) {
            // <p>wx<img/>yz</p> => <p>wx</p><p><img/></p><p>yz</p>
            const block = this.dependencies.split.splitAroundUntil(image, closestBlock(image));
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
            // Figure is contenteditable="false", so selection would jump
            // to the nearest editable sibling <div>. Setting cursor at
            // the end ensures caption input receives focus correctly.
            this.dependencies.selection.setCursorEnd(figure);
        }
        // Set the caption and its ID.
        const captionId = this.getCaptionId();
        this.captionsBeingAdded.add(captionId);
        image.setAttribute("data-caption-id", captionId);
        image.setAttribute("data-caption", captionText || "");
        // Ensure it's not possible to write inside the figure.
        figure.setAttribute("contenteditable", "false");
        image.classList.add(EDITABLE_MEDIA_CLASS);
        // Add the caption component.
        // => <p><figure><img/><figcaption>...</figcaption></figure></p>
        // or <p><a><figure><img/><figcaption>...</figcaption></figure></a></p>
        const caption = renderToElement("html_editor.EmbeddedCaptionBlueprint", {
            embeddedProps: JSON.stringify({
                id: captionId,
                focusInput,
            }),
        });
        figure.append(caption);
        this.dependencies.history.addStep();
        this.captionsBeingAdded.delete(captionId);
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
            // Select the image.
            const [anchorNode, anchorOffset, focusNode, focusOffset] = boundariesOut(image);
            this.dependencies.selection.setSelection({
                anchorNode,
                anchorOffset,
                focusNode,
                focusOffset,
            });
            this.dependencies.selection.focusEditable();
            this.dependencies.history.addStep();
        }
    }

    setupNewCaption({ name, props }) {
        if (name === "caption") {
            const id = props.id;
            delete props.id;
            const image = this.editable.querySelector(`img[data-caption-id="${id}"]`);
            Object.assign(props, {
                image,
                onUpdateCaption: (caption = "") => {
                    const figcaption = image.parentElement.querySelector("figcaption");
                    if (figcaption && figcaption.getAttribute("placeholder") !== caption) {
                        // Adapt the figcaption element's placeholder to the new
                        // caption for screen reader users.
                        figcaption.setAttribute("placeholder", caption);
                    }
                    if (caption !== image.getAttribute("data-caption")) {
                        image.setAttribute("data-caption", caption);
                    }
                    if (!this.captionsBeingAdded?.has(id)) {
                        // If the caption is being added, we update without
                        // adding a history step because it will be added at the
                        // end of adding the caption, by `addImageCaption`.
                        this.dependencies.history.addStep();
                    }
                },
                onEditorHistoryApply: (redo = false) => {
                    if (redo) {
                        this.dependencies.history.redo();
                    } else {
                        this.dependencies.history.undo();
                    }
                },
            });
        }
    }

    getImageName(image) {
        if (closestElement(image, "figure")) {
            return image.getAttribute("data-caption");
        }
    }

    isLinkAllowedOnSelection() {
        const figure = findInSelection(
            this.dependencies.selection.getEditableSelection(),
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
        if (media.nodeName === "IMG" && figure) {
            const [anchorNode, anchorOffset] = rightPos(figure);
            const caption = figure.querySelector("[data-embedded='caption'] input")?.value;
            figure.before(media);
            figure.remove();
            this.addImageCaption(media, caption, false);
            this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
        }
    }

    afterDelete() {
        const { anchorNode } = this.dependencies.selection.getEditableSelection();
        const targetedNodes = this.dependencies.selection.getTargetedNodes();
        for (const figure of this.editable.querySelectorAll("figure:not(:has(img))")) {
            const isSelectionInFigure = targetedNodes.includes(figure) || anchorNode === figure;
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
