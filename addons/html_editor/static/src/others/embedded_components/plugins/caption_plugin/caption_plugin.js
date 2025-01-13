import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { closestBlock } from "@html_editor/utils/blocks";
import { renderToElement } from "@web/core/utils/render";
import { fillEmpty, unwrapContents } from "@html_editor/utils/dom";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { boundariesOut, rightPos } from "@html_editor/utils/position";

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
                description: _t("Add/remove a caption"),
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
            (node) => ["FIGURE", "FIGCAPTION"].includes(node.nodeName), // avoid merge
        ],
    };

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

    toggleImageCaption(image = this.dependencies.image.getSelectedImage()) {
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
            closestBlock(image) !== this.editable
        ) {
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
        // Set the caption and its ID.
        const captionId = this.getCaptionId();
        this.captionsBeingAdded.add(captionId);
        image.setAttribute("data-caption-id", captionId);
        image.setAttribute("data-caption", captionText || "");
        // Ensure it's not possible to write inside the figure.
        figure.setAttribute("contenteditable", "false");
        // Ensure it's possible to write before and after the figure.
        const block = closestBlock(link || image);
        if (!block.previousSibling) {
            const baseContainer = this.dependencies.baseContainer.createBaseContainer();
            block.before(baseContainer);
            fillEmpty(baseContainer);
        }
        if (!block.nextSibling) {
            const baseContainer = this.dependencies.baseContainer.createBaseContainer();
            block.after(baseContainer);
            fillEmpty(baseContainer);
        }
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

    onImageReplaced(media) {
        const figure = closestElement(media, "figure");
        if (media.nodeName === "IMG" && figure) {
            const caption = figure.querySelector("[data-embedded='caption'] input")?.value;
            if (caption) {
                media.setAttribute("data-caption", caption);
            }
            const [anchorNode, anchorOffset] = rightPos(figure);
            this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
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
