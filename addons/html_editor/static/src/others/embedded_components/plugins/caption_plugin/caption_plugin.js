import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { closestBlock } from "@html_editor/utils/blocks";
import { isEmptyBlock } from "@html_editor/utils/dom_info";
import { renderToElement } from "@web/core/utils/render";
import { fillEmpty } from "@html_editor/utils/dom";
import { closestElement } from "@html_editor/utils/dom_traversal";

export class CaptionPlugin extends Plugin {
    static id = "caption";
    static dependencies = ["image", "media", "split", "history", "embeddedComponents"];
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
            const image = figure.querySelector("img");
            // remove embedding and convert caption attribute to text
            figure.querySelector("figcaption").remove();
            const caption = root.ownerDocument.createElement("figcaption");
            caption.textContent = image.getAttribute("data-caption");
            image.removeAttribute("data-caption");
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

    toggleImageCaption(image, captionText) {
        image = image || this.dependencies.image.getSelectedImage();
        if (!image) {
            return;
        }
        if (this.hasImageCaption(image)) {
            this.removeImageCaption(image);
        } else {
            this.addImageCaption(image, captionText);
        }
    }

    addImageCaption(image, captionText, focusInput = true) {
        image = image || this.dependencies.image.getSelectedImage();
        if (!image) {
            return;
        }
        // Move the image within a figure element.
        const blockParent = closestBlock(image);
        if (blockParent !== this.editable) {
            this.dependencies.split.splitAroundUntil(
                image,
                closestBlock(blockParent),
            );
        }
        let block = closestBlock(image);
        if (block === this.editable) {
            block = image;
        }
        if (isEmptyBlock(block.previousSibling)) {
            block.previousSibling.remove();
        }
        if (isEmptyBlock(block.nextSibling)) {
            block.nextSibling.remove();
        }
        const figure = this.document.createElement("figure");
        block.before(figure);
        figure.append(image);
        if (isEmptyBlock(block)) {
            block.remove();
        };
        // Add the caption component.
        const captionId = "" + Math.floor(Math.random() * Date.now());
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
        if (!figure.previousSibling) {
            const p = this.document.createElement("p")
            figure.before(p);
            fillEmpty(p);
        }
        if (!figure.nextSibling) {
            const p = this.document.createElement("p")
            figure.after(p);
            fillEmpty(p);
        }
        // Set the caption.
        if (captionText) {
            image.setAttribute("data-caption", captionText);
        }
        this.dependencies.history.addStep();
    }

    removeImageCaption(image) {
        const figure = closestElement(image, "figure");
        if (figure) {
            const p = this.document.createElement("p");
            p.append(image);
            figure.before(p);
            image.removeAttribute("data-caption-id");
            figure.remove();
            this.dependencies.history.addStep();
        }
    }

    setupNewCaption({ name, props }) {
        if (name === "caption") {
            Object.assign(props, {
                editable: this.editable,
                addHistoryStep: this.dependencies.history.addStep,
            });
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
            figure.remove();
            this.dependencies.history.addStep();
            return true;
        }
    }
}