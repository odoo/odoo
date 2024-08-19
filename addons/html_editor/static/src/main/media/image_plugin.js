import { Plugin } from "../../plugin";
import { _t } from "@web/core/l10n/translation";
import { isImageUrl } from "@html_editor/utils/url";
import { ImageDescription } from "./image_description";
import { ImagePadding } from "./image_padding";
import { createFileViewer } from "@web/core/file_viewer/file_viewer_hook";

function hasShape(imagePlugin, shapeName) {
    return () => imagePlugin.isSelectionShaped(shapeName);
}

export class ImagePlugin extends Plugin {
    static name = "image";
    static dependencies = ["history", "link", "powerbox", "dom", "selection"];
    /** @type { (p: ImagePlugin) => Record<string, any> } */
    static resources(p) {
        return {
            handle_paste_url: p.handlePasteUrl.bind(p),
            onSelectionChange: p.onSelectionChange.bind(p),
            toolbarNamespace: [
                {
                    id: "image",
                    isApplied: (traversedNodes) => {
                        return traversedNodes.at(-1)?.tagName === "IMG";
                    },
                },
            ],
            toolbarCategory: [
                {
                    id: "image_preview",
                    sequence: 23,
                    namespace: "image",
                },
                { id: "image_description", sequence: 24, namespace: "image" },
                { id: "image_shape", sequence: 25, namespace: "image" },
                { id: "image_padding", sequence: 26, namespace: "image" },
                {
                    id: "image_size",
                    sequence: 26,
                    namespace: "image",
                },
                { id: "image_transform", sequence: 26, namespace: "image" },
                { id: "image_delete", sequence: 30, namespace: "image" },
            ],
            toolbarItems: [
                {
                    id: "image_preview",
                    category: "image_preview",
                    action(dispatch) {
                        dispatch("PREVIEW_IMAGE");
                    },
                    icon: "fa-search-plus",
                    name: _t("Preview image"),
                },
                {
                    id: "image_description",
                    category: "image_description",
                    Component: ImageDescription,
                    props: {
                        getDescription: () => p.getImageAttribute("alt"),
                        getTooltip: () => p.getImageAttribute("title"),
                        dispatch: p.dispatch.bind(p),
                        getSelection: p.shared.getEditableSelection.bind(p),
                    },
                },
                {
                    id: "shape_rounded",
                    category: "image_shape",
                    action(dispatch) {
                        dispatch("SHAPE_ROUNDED");
                    },
                    name: _t("Shape: Rounded"),
                    icon: "fa-square",
                    isFormatApplied: hasShape(p, "rounded"),
                },
                {
                    id: "shape_circle",
                    category: "image_shape",
                    action(dispatch) {
                        dispatch("SHAPE_CIRCLE");
                    },
                    name: _t("Shape: Circle"),
                    icon: "fa-circle-o",
                    isFormatApplied: hasShape(p, "rounded-circle"),
                },
                {
                    id: "shape_shadow",
                    category: "image_shape",
                    action(dispatch) {
                        dispatch("SHAPE_SHADOW");
                    },
                    name: _t("Shape: Shadow"),
                    icon: "fa-sun-o",
                    isFormatApplied: hasShape(p, "shadow"),
                },
                {
                    id: "shape_thumbnail",
                    category: "image_shape",
                    action(dispatch) {
                        dispatch("SHAPE_THUMBNAIL");
                    },
                    name: _t("Shape: Thumbnail"),
                    icon: "fa-picture-o",
                    isFormatApplied: hasShape(p, "img-thumbnail"),
                },
                {
                    id: "image_padding",
                    category: "image_padding",
                    name: _t("Image padding"),
                    Component: ImagePadding,
                    props: {
                        dispatch: p.dispatch.bind(p),
                    },
                },
                {
                    id: "resize_default",
                    category: "image_size",
                    action(dispatch) {
                        dispatch("RESIZE_IMAGE", "");
                    },
                    name: _t("Resize Default"),
                    text: _t("Default"),
                    isFormatApplied: () => p.hasImageSize(""),
                },
                {
                    id: "resize_100",
                    category: "image_size",
                    action(dispatch) {
                        dispatch("RESIZE_IMAGE", "100%");
                    },
                    name: _t("Resize Full"),
                    text: "100%",
                    isFormatApplied: () => p.hasImageSize("100%"),
                },
                {
                    id: "resize_50",
                    category: "image_size",
                    action(dispatch) {
                        dispatch("RESIZE_IMAGE", "50%");
                    },
                    name: _t("Resize Half"),
                    text: "50%",
                    isFormatApplied: () => p.hasImageSize("50%"),
                },
                {
                    id: "resize_25",
                    category: "image_size",
                    action(dispatch) {
                        dispatch("RESIZE_IMAGE", "25%");
                    },
                    name: _t("Resize Quarter"),
                    text: "25%",
                    isFormatApplied: () => p.hasImageSize("25%"),
                },
                {
                    id: "image_transform",
                    category: "image_transform",
                    action(dispatch) {
                        dispatch("TRANSFORM_IMAGE");
                    },
                    name: _t("Transform the picture (click twice to reset transformation)"),
                    icon: "fa-object-ungroup",
                    isFormatApplied: () => p.currentImageTransformation.imageEl,
                },
                {
                    id: "image_delete",
                    category: "image_delete",
                    action(dispatch) {
                        dispatch("DELETE_IMAGE");
                    },
                    name: _t("Remove (DELETE)"),
                    icon: "fa-trash text-danger",
                },
            ],
        };
    }

    setup() {
        this.addDomListener(this.editable, "pointerup", (e) => {
            if (e.target.tagName === "IMG") {
                const range = this.document.createRange();
                range.selectNode(e.target);
                this.shared.setSelection({
                    anchorNode: range.startContainer,
                    anchorOffset: range.startOffset,
                    focusNode: range.endContainer,
                    focusOffset: range.endOffset,
                });
            }
        });
        this.fileViewer = createFileViewer();

        this.currentImageTransformation = {
            imageEl: undefined,
            clean: undefined,
        };
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
            case "SHAPE_SHADOW":
            case "SHAPE_CIRCLE":
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
                const $selectedImg = $(selectedImg);
                $selectedImg.transfo({ document: this.document });
                this.currentImageTransformation = {
                    clean: () => {
                        $selectedImg.transfo("destroy");
                        this.currentImageTransformation.clean = undefined;
                        this.currentImageTransformation.imageEl = undefined;
                    },
                    imageEl: selectedImg,
                };
                break;
            }
            case "CONTENT_UPDATED": {
                if (
                    this.currentImageTransformation.imageEl &&
                    payload.root === this.currentImageTransformation.imageEl
                ) {
                    this.dispatch("ADD_STEP");
                }
                break;
            }
            case "DELETE_IMAGE": {
                const selectedImg = this.getSelectedImage();
                if (selectedImg) {
                    selectedImg.remove();
                    this.currentImageTransformation.clean?.();
                    this.dispatch("ADD_STEP");
                }
            }
        }
    }

    onSelectionChange() {
        this.currentImageTransformation.clean?.();
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
}
