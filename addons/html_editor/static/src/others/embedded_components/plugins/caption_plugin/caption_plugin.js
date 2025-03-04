import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { closestBlock } from "@html_editor/utils/blocks";
import { renderToElement } from "@web/core/utils/render";
import { fillEmpty, unwrapContents } from "@html_editor/utils/dom";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { boundariesOut } from "@html_editor/utils/position";

export class CaptionPlugin extends Plugin {
    static id = "caption";
    static dependencies = ["image", "media", "split", "history", "embeddedComponents", "selection", "baseContainer"];
    resources = {
        user_commands: [
            {
                id: "toggleImageCaption",
                title: _t("Add/remove a caption"),
                run: this.toggleImageCaption.bind(this),
            },
        ],
        toolbar_items: [
            {
                id: "image_caption",
                title: _t("Add/remove a caption"),
                groupId: "image_description",
                commandId: "toggleImageCaption",
                text: "Caption",
                isActive: () => this.hasImageCaption(this.dependencies.image.getSelectedImage()),
            },
        ],
        clean_for_save_handlers: this.cleanForSave.bind(this),
        mount_component_handlers: this.setupNewCaption.bind(this),
        delete_image_handlers: this.handleDeleteImage.bind(this),
        afer_save_media_dialog_handlers: this.onImageReplaced.bind(this),
        hints: [{ selector: "FIGCAPTION", text: _t("Write a caption...") }],
        unsplittable_node_predicates: [
            node => ["FIGURE", "FIGCAPTION"].includes(node.nodeName) // avoid merge
        ],
        image_name_predicates: [
            this.getImageName.bind(this),
        ],
    }

    setup() {
        for (const figure of this.editable.querySelectorAll("figure")) {
            // Embed the captions.
            const image = figure.querySelector("img");
            figure.before(image);
            const caption = figure.querySelector("figcaption").textContent;
            figure.remove();
            this.addImageCaption(image, caption, false);
        }
    }

    destroy() {
        super.destroy();
    }

    cleanForSave({ root }) {
        for (const figure of root.querySelectorAll("figure")) {
            figure.removeAttribute("contenteditable");
            const image = figure.querySelector("img");
            // remove embedding and convert caption attribute to text
            figure.querySelector("figcaption").remove();
            const caption = root.ownerDocument.createElement("figcaption");
            caption.textContent = image.getAttribute("data-caption");
            image.removeAttribute("data-caption");
            this.dependencies.media.unmarkMediaAsEditable(image);
            image.removeAttribute("data-caption-id");
            image.after(caption);
        }
    }

    hasImageCaption(image) {
        if (!image) {
            return;
        }
        const block = closestBlock(image);
        return block.nodeName === "FIGURE" && !!block.querySelector("[data-embedded='caption'] input");
    }

    toggleImageCaption(image) {
        image = image || this.dependencies.image.getSelectedImage();
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
        image = image || this.dependencies.image.getSelectedImage();
        if (!image) {
            return;
        }
        // Move the image within a figure element.
        const figure = this.document.createElement("figure");
        const link = image.parentElement.nodeName === "A" && image.parentElement;
        if (link && (link.previousSibling || link.nextSibling)) {
            // <p>wx<a><img/></a>yz</p> => <p>wx</p><p><a><img/></a></p><p>yz</p>
            this.dependencies.split.splitAroundUntil(link, closestBlock(link));
        } else if (!link && (image.previousSibling || image.nextSibling) && closestBlock(image) !== this.editable) {
            // <p>wx<img/>yz</p> => <p>wx</p><p><img/></p><p>yz</p>
            this.dependencies.split.splitAroundUntil(image, closestBlock(image));
        }
        // => <p><figure><img/></figure></p>
        // or <p><a><figure><img/></figure></a></p>
        image.before(figure);
        figure.append(image);
        if (!link && figure.parentElement !== this.editable) {
            // => <figure><img/></figure></p>
            // but still <p><a><figure><img/></figure></p>
            unwrapContents(figure.parentElement);
        }
        // Add the caption component.
        // => <p><figure><img/><figcaption>...</figcaption></figure></p>
        // or <p><a><figure><img/><figcaption>...</figcaption></figure></a></p>
        const captionId = this.getCaptionId();
        image.setAttribute("data-caption-id", captionId);
        const caption = renderToElement("html_editor.EmbeddedCaptionBlueprint", {
            embeddedProps: JSON.stringify({
                id: captionId,
                focusInput,
            }),
        });
        figure.append(caption);
        // Ensure it's not possible to write inside the figure.
        figure.setAttribute("contenteditable", "false");
        this.dependencies.media.markMediaAsEditable(image); // Needed because the image is in a non-editable container.
        // Ensure it's possible to write before and after the figure.
        const block = closestBlock(link || image);
        if (!block.previousSibling) {
            const p = this.document.createElement("p")
            block.before(p);
            fillEmpty(p);
        }
        if (!block.nextSibling) {
            const p = this.document.createElement("p")
            block.after(p);
            fillEmpty(p);
        }
        // Set the caption.
        image.setAttribute("data-caption", captionText || "");
        this.dependencies.history.addStep();
    }

    removeImageCaption(image) {
        const figure = closestElement(image, "figure");
        if (figure) {
            figure.querySelector("figcaption").remove();
            if (closestBlock(figure.parentElement) === this.editable) {
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
            this.dependencies.media.unmarkMediaAsEditable(image);
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
            Object.assign(props, {
                editable: this.editable,
                addHistoryStep: this.dependencies.history.addStep,
                undo: this.dependencies.history.undo,
                redo: this.dependencies.history.redo,
            });
        }
    }

    getImageName(image) {
        if (closestElement(image, "figure")) {
            return image.getAttribute("data-caption");
        }
    }

    onImageReplaced(media) {
        const figure = closestElement(media, "figure");
        if (media.nodeName === "IMG" && figure) {
            const caption = figure.querySelector("[data-embedded='caption'] input")?.value;
            if (caption) {
                media.setAttribute("data-caption", caption);
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
}