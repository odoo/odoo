import { registry } from "@web/core/registry";
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

            toolbarGroup: [
                {
                    id: "image_preview",
                    sequence: 23,
                    namespace: "IMG",
                    buttons: [
                        {
                            id: "image_preview",
                            cmd: "PREVIEW_IMAGE",
                            icon: "fa-search-plus",
                            name: "Preview image",
                        },
                    ],
                },
                {
                    id: "image_description",
                    sequence: 24,
                    namespace: "IMG",
                    buttons: [
                        {
                            id: "image_description",
                            Component: ImageDescription,
                            props: {
                                getDescription: () => p.getImageAttribute("alt"),
                                getTooltip: () => p.getImageAttribute("title"),
                            },
                        },
                    ],
                },
                {
                    id: "image_shape",
                    sequence: 25,
                    namespace: "IMG",
                    buttons: [
                        {
                            id: "shape_rounded",
                            cmd: "SHAPE_ROUNDED",
                            name: "Shape: Rounded",
                            icon: "fa-square",
                            isFormatApplied: hasShape(p, "rounded"),
                        },
                        {
                            id: "shape_circle",
                            cmd: "SHAPE_CIRCLE",
                            name: "Shape: Circle",
                            icon: "fa-circle-o",
                            isFormatApplied: hasShape(p, "rounded-circle"),
                        },
                        {
                            id: "shape_shadow",
                            cmd: "SHAPE_SHADOW",
                            name: "Shape: Shadow",
                            icon: "fa-sun-o",
                            isFormatApplied: hasShape(p, "shadow"),
                        },
                        {
                            id: "shape_thumbnail",
                            cmd: "SHAPE_THUMBNAIL",
                            name: "Shape: Thumbnail",
                            icon: "fa-picture-o",
                            isFormatApplied: hasShape(p, "img-thumbnail"),
                        },
                    ],
                },
                {
                    id: "image_padding",
                    sequence: 26,
                    namespace: "IMG",
                    buttons: [
                        {
                            id: "image_padding",
                            name: "Image padding",
                            Component: ImagePadding,
                        },
                    ],
                },
                {
                    id: "image_size",
                    sequence: 26,
                    namespace: "IMG",
                    buttons: [
                        {
                            id: "resize_default",
                            cmd: "RESIZE_IMAGE",
                            cmdPayload: "",
                            title: "Size: Default",
                            text: "Default",
                            isFormatApplied: () => p.hasImageSize(""),
                        },
                        {
                            id: "resize_100",
                            cmd: "RESIZE_IMAGE",
                            cmdPayload: "100%",
                            title: "Size: 100%",
                            text: "100%",
                            isFormatApplied: () => p.hasImageSize("100%"),
                        },
                        {
                            id: "resize_50",
                            cmd: "RESIZE_IMAGE",
                            cmdPayload: "50%",
                            title: "Size: 50%",
                            text: "50%",
                            isFormatApplied: () => p.hasImageSize("50%"),
                        },
                        {
                            id: "resize_25",
                            cmd: "RESIZE_IMAGE",
                            cmdPayload: "25%",
                            title: "Size: 25%",
                            text: "25%",
                            isFormatApplied: () => p.hasImageSize("25%"),
                        },
                    ],
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
                selectedImg.classList.toggle(commandToClassNameDict[command]);
                this.dispatch("ADD_STEP");
                break;
            }
            case "UPDATE_IMAGE_DESCRIPTION": {
                const selectedImg = this.getSelectedImage();
                selectedImg.setAttribute("alt", payload.description);
                selectedImg.setAttribute("title", payload.tooltip);
                this.dispatch("ADD_STEP");
                break;
            }
            case "RESIZE_IMAGE": {
                const selectedImg = this.getSelectedImage();
                selectedImg.style.width = payload;
                this.dispatch("ADD_STEP");
                break;
            }
            case "SET_IMAGE_PADDING": {
                const selectedImg = this.getSelectedImage();
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
        }
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
registry.category("phoenix_plugins").add(ImagePlugin.name, ImagePlugin);
