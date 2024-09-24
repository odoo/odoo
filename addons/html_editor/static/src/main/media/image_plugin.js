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
        handle_paste_url: this.handlePasteUrl.bind(this),
        onSelectionChange: this.onSelectionChange.bind(this),
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
                action(dispatch) {
                    dispatch("PREVIEW_IMAGE");
                },
                icon: "fa-search-plus",
                title: _t("Preview image"),
            },
            {
                id: "image_description",
                title: _t("Edit media description"),
                category: "image_description",
                Component: ImageDescription,
                props: {
                    getDescription: () => this.getImageAttribute("alt"),
                    getTooltip: () => this.getImageAttribute("title"),
                },
            },
            {
                id: "shape_rounded",
                category: "image_shape",
                action(dispatch) {
                    dispatch("SHAPE_ROUNDED");
                },
                title: _t("Shape: Rounded"),
                icon: "fa-square",
                isFormatApplied: hasShape(this, "rounded"),
            },
            {
                id: "shape_circle",
                category: "image_shape",
                action(dispatch) {
                    dispatch("SHAPE_CIRCLE");
                },
                title: _t("Shape: Circle"),
                icon: "fa-circle-o",
                isFormatApplied: hasShape(this, "rounded-circle"),
            },
            {
                id: "shape_shadow",
                category: "image_shape",
                action(dispatch) {
                    dispatch("SHAPE_SHADOW");
                },
                title: _t("Shape: Shadow"),
                icon: "fa-sun-o",
                isFormatApplied: hasShape(this, "shadow"),
            },
            {
                id: "shape_thumbnail",
                category: "image_shape",
                action(dispatch) {
                    dispatch("SHAPE_THUMBNAIL");
                },
                title: _t("Shape: Thumbnail"),
                icon: "fa-picture-o",
                isFormatApplied: hasShape(this, "img-thumbnail"),
            },
            {
                id: "image_padding",
                category: "image_padding",
                title: _t("Image padding"),
                Component: ImagePadding,
            },
            {
                id: "resize_default",
                category: "image_size",
                action(dispatch) {
                    dispatch("RESIZE_IMAGE", "");
                },
                title: _t("Resize Default"),
                text: _t("Default"),
                isFormatApplied: () => this.hasImageSize(""),
            },
            {
                id: "resize_100",
                category: "image_size",
                action(dispatch) {
                    dispatch("RESIZE_IMAGE", "100%");
                },
                title: _t("Resize Full"),
                text: "100%",
                isFormatApplied: () => this.hasImageSize("100%"),
            },
            {
                id: "resize_50",
                category: "image_size",
                action(dispatch) {
                    dispatch("RESIZE_IMAGE", "50%");
                },
                title: _t("Resize Half"),
                text: "50%",
                isFormatApplied: () => this.hasImageSize("50%"),
            },
            {
                id: "resize_25",
                category: "image_size",
                action(dispatch) {
                    dispatch("RESIZE_IMAGE", "25%");
                },
                title: _t("Resize Quarter"),
                text: "25%",
                isFormatApplied: () => this.hasImageSize("25%"),
            },
            {
                id: "image_transform",
                category: "image_transform",
                action(dispatch) {
                    dispatch("TRANSFORM_IMAGE");
                },
                title: _t("Transform the picture (click twice to reset transformation)"),
                icon: "fa-object-ungroup",
                isFormatApplied: () => this.isImageTransformationOpen(),
            },
            {
                id: "image_delete",
                category: "image_delete",
                action(dispatch) {
                    dispatch("DELETE_IMAGE");
                },
                title: _t("Remove (DELETE)"),
                icon: "fa-trash text-danger",
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

    handleCommand(command, payload) {
        const commandToClassNameDict = {
            SHAPE_ROUNDED: "rounded",
            SHAPE_SHADOW: "shadow",
            SHAPE_CIRCLE: "rounded-circle",
            SHAPE_THUMBNAIL: "img-thumbnail",
        };

        switch (command) {
            case "SHAPE_ROUNDED":
            case "SHAPE_CIRCLE": {
                const selectedImg = this.getSelectedImage();
                if (!selectedImg) {
                    return;
                }
                const mutuallyExclusiveShapes = {
                    SHAPE_ROUNDED: "rounded-circle",
                    SHAPE_CIRCLE: "rounded",
                };
                selectedImg.classList.remove(mutuallyExclusiveShapes[command]);
                selectedImg.classList.toggle(commandToClassNameDict[command]);
                this.dispatch("ADD_STEP");
                break;
            }
            case "SHAPE_SHADOW":
            case "SHAPE_THUMBNAIL": {
                const selectedImg = this.getSelectedImage();
                if (!selectedImg) {
                    return;
                }
                selectedImg.classList.toggle(commandToClassNameDict[command]);
                this.dispatch("ADD_STEP");
                break;
            }
            case "UPDATE_IMAGE_DESCRIPTION": {
                const selectedImg = this.getSelectedImage();
                if (!selectedImg) {
                    return;
                }
                selectedImg.setAttribute("alt", payload.description);
                selectedImg.setAttribute("title", payload.tooltip);
                this.dispatch("ADD_STEP");
                break;
            }
            case "RESIZE_IMAGE": {
                const selectedImg = this.getSelectedImage();
                if (!selectedImg) {
                    return;
                }
                selectedImg.style.width = payload;
                this.dispatch("ADD_STEP");
                break;
            }
            case "SET_IMAGE_PADDING": {
                const selectedImg = this.getSelectedImage();
                if (!selectedImg) {
                    return;
                }
                for (const classString of selectedImg.classList) {
                    if (classString.match(/^p-[0-9]$/)) {
                        selectedImg.classList.remove(classString);
                    }
                }
                selectedImg.classList.add(`p-${payload.padding}`);
                this.dispatch("ADD_STEP");
                break;
            }
            case "PREVIEW_IMAGE": {
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
                break;
            }
            case "TRANSFORM_IMAGE": {
                const selectedImg = this.getSelectedImage();
                if (!selectedImg) {
                    return;
                }
                this.openImageTransformation(selectedImg);
                break;
            }
            case "DELETE_IMAGE": {
                const selectedImg = this.getSelectedImage();
                if (selectedImg) {
                    selectedImg.remove();
                    this.closeImageTransformation();
                    this.dispatch("ADD_STEP");
                }
            }
        }
    }

    onSelectionChange() {
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
            this.dispatch("ADD_STEP");
            const embedImageCommand = {
                name: _t("Embed Image"),
                description: _t("Embed the image in the document."),
                fontawesome: "fa-image",
                action: () => {
                    const img = document.createElement("IMG");
                    img.setAttribute("src", url);
                    this.shared.domInsert(img);
                    this.dispatch("ADD_STEP");
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
        registry.category("main_components").add("ImageTransformation", {
            Component: ImageTransformation,
            props: {
                image,
                document: this.document,
                destroy: this.closeImageTransformation,
                onChange: () => this.dispatch("ADD_STEP"),
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
}
