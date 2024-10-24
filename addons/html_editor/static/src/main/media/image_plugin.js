import { Plugin } from "../../plugin";
import { _t } from "@web/core/l10n/translation";
import { isImageUrl } from "@html_editor/utils/url";
import { ImageDescription } from "./image_description";
import { ImagePadding } from "./image_padding";
import { createFileViewer } from "@web/core/file_viewer/file_viewer_hook";
import { boundariesOut } from "@html_editor/utils/position";
import { ImageTransformation } from "./image_transformation";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";

function hasShape(imagePlugin, shapeName) {
    return () => imagePlugin.isSelectionShaped(shapeName);
}

export class ImagePlugin extends Plugin {
    static name = "image";
    static dependencies = ["history", "link", "powerbox", "dom", "selection"];
    resources = {
        user_commands: [
            {
                id: "deleteImage",
                label: _t("Remove (DELETE)"),
                icon: "fa-trash text-danger",
                run: this.deleteImage.bind(this),
            },
            {
                id: "previewImage",
                label: _t("Preview image"),
                icon: "fa-search-plus",
                run: this.previewImage.bind(this),
            },
            {
                id: "setImageShapeRounded",
                label: _t("Shape: Rounded"),
                icon: "fa-square",
                run: () => this.setImageShape("rounded", { excludeClasses: ["rounded-circle"] }),
            },
            {
                id: "setImageShapeCircle",
                label: _t("Shape: Circle"),
                icon: "fa-circle-o",
                run: () => this.setImageShape("rounded-circle", { excludeClasses: ["rounded"] }),
            },
            {
                id: "setImageShapeShadow",
                label: _t("Shape: Shadow"),
                icon: "fa-sun-o",
                run: () => this.setImageShape("shadow"),
            },
            {
                id: "setImageShapeThumbnail",
                label: _t("Shape: Thumbnail"),
                icon: "fa-picture-o",
                run: () => this.setImageShape("img-thumbnail"),
            },
            { id: "resizeImage", run: this.resizeImage.bind(this) },
            {
                id: "transformImage",
                label: _t("Transform the picture (click twice to reset transformation)"),
                icon: "fa-object-ungroup",
                run: this.transformImage.bind(this),
            },
            { id: "setImagePadding", run: this.setImagePadding.bind(this) },
        ],
        paste_url_overrides: this.handlePasteUrl.bind(this),
        selectionchange_handlers: this.onSelectionChange.bind(this),
        toolbarNamespace: [
            {
                id: "image",
                isApplied: (traversedNodes) =>
                    traversedNodes.every(
                        // All nodes should be images or its ancestors
                        (node) => node.nodeName === "IMG" || node.querySelector?.("img")
                    ),
            },
        ],
        toolbarCategory: [
            withSequence(23, {
                id: "image_preview",
                namespace: "image",
            }),
            withSequence(24, { id: "image_description", namespace: "image" }),
            withSequence(25, { id: "image_shape", namespace: "image" }),
            withSequence(26, { id: "image_padding", namespace: "image" }),
            withSequence(26, {
                id: "image_size",
                namespace: "image",
            }),
            withSequence(26, { id: "image_transform", namespace: "image" }),
            withSequence(30, { id: "image_delete", namespace: "image" }),
        ],
        toolbarItems: [
            {
                id: "image_preview",
                category: "image_preview",
                commandId: "previewImage",
            },
            {
                id: "image_description",
                label: _t("Edit media description"),
                category: "image_description",
                Component: ImageDescription,
                props: {
                    getDescription: () => this.getImageAttribute("alt"),
                    getTooltip: () => this.getImageAttribute("title"),
                    updateImageDescription: this.updateImageDescription.bind(this),
                },
            },
            {
                id: "shape_rounded",
                category: "image_shape",
                commandId: "setImageShapeRounded",
                isFormatApplied: hasShape(this, "rounded"),
            },
            {
                id: "shape_circle",
                category: "image_shape",
                commandId: "setImageShapeCircle",
                isFormatApplied: hasShape(this, "rounded-circle"),
            },
            {
                id: "shape_shadow",
                category: "image_shape",
                commandId: "setImageShapeShadow",
                isFormatApplied: hasShape(this, "shadow"),
            },
            {
                id: "shape_thumbnail",
                category: "image_shape",
                commandId: "setImageShapeThumbnail",
                isFormatApplied: hasShape(this, "img-thumbnail"),
            },
            {
                id: "image_padding",
                category: "image_padding",
                label: _t("Image padding"),
                Component: ImagePadding,
                props: {
                    onSelected: this.setImagePadding.bind(this),
                },
            },
            {
                id: "resize_default",
                category: "image_size",
                commandId: "resizeImage",
                label: _t("Resize Default"),
                text: _t("Default"),
                isFormatApplied: () => this.hasImageSize(""),
            },
            {
                id: "resize_100",
                category: "image_size",
                commandId: "resizeImage",
                commandParams: { size: "100%" },
                label: _t("Resize Full"),
                text: "100%",
                isFormatApplied: () => this.hasImageSize("100%"),
            },
            {
                id: "resize_50",
                category: "image_size",
                commandId: "resizeImage",
                commandParams: { size: "50%" },
                label: _t("Resize Half"),
                text: "50%",
                isFormatApplied: () => this.hasImageSize("50%"),
            },
            {
                id: "resize_25",
                category: "image_size",
                commandId: "resizeImage",
                commandParams: { size: "25%" },
                label: _t("Resize Quarter"),
                text: "25%",
                isFormatApplied: () => this.hasImageSize("25%"),
            },
            {
                id: "image_transform",
                category: "image_transform",
                commandId: "transformImage",
                isFormatApplied: () => this.isImageTransformationOpen(),
            },
            {
                id: "image_delete",
                category: "image_delete",
                commandId: "deleteImage",
            },
        ],
    };

    setup() {
        this.addDomListener(this.editable, "pointerup", (e) => {
            if (e.target.tagName === "IMG") {
                const [anchorNode, anchorOffset, focusNode, focusOffset] = boundariesOut(e.target);
                this.shared.setSelection({ anchorNode, anchorOffset, focusNode, focusOffset });
                this.shared.focusEditable();
            }
        });
        this.fileViewer = createFileViewer();
    }

    destroy() {
        super.destroy();
        this.closeImageTransformation();
    }

    setImagePadding({ size } = {}) {
        const selectedImg = this.getSelectedImage();
        if (!selectedImg) {
            return;
        }
        for (const classString of selectedImg.classList) {
            if (classString.match(/^p-[0-9]$/)) {
                selectedImg.classList.remove(classString);
            }
        }
        selectedImg.classList.add(`p-${size}`);
        this.shared.addStep();
    }
    resizeImage({ size } = {}) {
        const selectedImg = this.getSelectedImage();
        if (!selectedImg) {
            return;
        }
        selectedImg.style.width = size || "";
        this.shared.addStep();
    }

    transformImage() {
        const selectedImg = this.getSelectedImage();
        if (!selectedImg) {
            return;
        }
        this.openImageTransformation(selectedImg);
    }

    setImageShape(className, { excludeClasses = [] } = {}) {
        const selectedImg = this.getSelectedImage();
        if (!selectedImg) {
            return;
        }
        for (const classString of excludeClasses) {
            if (selectedImg.classList.contains(classString)) {
                selectedImg.classList.remove(classString);
            }
        }
        selectedImg.classList.toggle(className);
        this.shared.addStep();
    }

    previewImage() {
        const selectedImg = this.getSelectedImage();
        if (!selectedImg) {
            return;
        }
        const fileModel = {
            isImage: true,
            isViewable: true,
            displayName: selectedImg.src,
            defaultSource: selectedImg.src,
            downloadUrl: selectedImg.src,
        };
        this.document.getSelection().collapseToEnd();
        this.fileViewer.open(fileModel);
    }

    deleteImage() {
        const selectedImg = this.getSelectedImage();
        if (selectedImg) {
            selectedImg.remove();
            this.closeImageTransformation();
            this.shared.addStep();
        }
    }

    onSelectionChange(selectionData) {
        const { anchorNode, focusNode } = selectionData.documentSelection;
        if (!anchorNode && !focusNode) {
            return;
        }
        this.closeImageTransformation();
    }

    getSelectedImage() {
        const selectedNodes = this.shared.getSelectedNodes();
        return selectedNodes.find((node) => node.tagName === "IMG");
    }

    hasImageSize(size) {
        const selectedImg = this.getSelectedImage();
        return selectedImg?.style?.width === size;
    }

    isSelectionShaped(shape) {
        const selectedNodes = this.shared
            .getTraversedNodes()
            .filter((n) => n.tagName === "IMG" && n.classList.contains(shape));
        return selectedNodes.length > 0;
    }

    getImageAttribute(attributeName) {
        const selectedNodes = this.shared.getSelectedNodes();
        const selectedImg = selectedNodes.find((node) => node.tagName === "IMG");
        return selectedImg.getAttribute(attributeName) || undefined;
    }

    /**
     * @param {string} text
     * @param {string} url
     */
    handlePasteUrl(text, url) {
        if (isImageUrl(url)) {
            const restoreSavepoint = this.shared.makeSavePoint();
            // Open powerbox with commands to embed media or paste as link.
            // Insert URL as text, revert it later if a command is triggered.
            this.shared.domInsert(text);
            this.shared.addStep();
            const embedImageCommand = {
                label: _t("Embed Image"),
                description: _t("Embed the image in the document."),
                icon: "fa-image",
                run: () => {
                    const img = document.createElement("IMG");
                    img.setAttribute("src", url);
                    this.shared.domInsert(img);
                    this.shared.addStep();
                },
            };
            const commands = [embedImageCommand, this.shared.getPathAsUrlCommand(text, url)];
            this.shared.openPowerbox({ commands, onApplyCommand: restoreSavepoint });
            return true;
        }
    }

    openImageTransformation(image) {
        if (registry.category("main_components").contains("ImageTransformation")) {
            return;
        }
        Promise.resolve().then(() => {
            this.document.getSelection()?.removeAllRanges();
        });
        registry.category("main_components").add("ImageTransformation", {
            Component: ImageTransformation,
            props: {
                image,
                document: this.document,
                destroy: () => this.closeImageTransformation(),
                onChange: () => this.shared.addStep(),
            },
        });
    }

    isImageTransformationOpen() {
        return registry.category("main_components").contains("ImageTransformation");
    }

    closeImageTransformation() {
        if (this.isImageTransformationOpen()) {
            registry.category("main_components").remove("ImageTransformation");
        }
    }
    updateImageDescription({ description, tooltip } = {}) {
        const selectedImg = this.getSelectedImage();
        if (!selectedImg) {
            return;
        }
        selectedImg.setAttribute("alt", description);
        selectedImg.setAttribute("title", tooltip);
        this.shared.addStep();
    }
}
