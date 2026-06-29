import { proxy } from "@odoo/owl";
import { Plugin } from "../../plugin";
import { _t } from "@web/core/l10n/translation";
import { isImageUrl } from "@html_editor/utils/url";
import { ImageToolbarDropdown } from "./image_toolbar_dropdown";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { boundariesOut } from "@html_editor/utils/position";
import { READ, withSequence } from "@html_editor/utils/resource";
import { callbacksForCursorUpdate } from "@html_editor/utils/selection";
import { closestBlock } from "@html_editor/utils/blocks";
import { fillEmpty } from "@html_editor/utils/dom";
import { isElementOverlappingAnyFloatingImage } from "@html_editor/utils/dom_info";
import { ImageAlignSelector } from "./image_align_selector";

const IMAGE_PADDING = [
    { name: _t("None"), value: 0 },
    { name: _t("Small"), value: 1 },
    { name: _t("Medium"), value: 2 },
    { name: _t("Large"), value: 3 },
    { name: _t("XL"), value: 5 },
];

const IMAGE_SIZE = [
    { name: _t("Default"), value: "" },
    { name: _t("100%"), value: "100%" },
    { name: _t("50%"), value: "50%" },
    { name: _t("25%"), value: "25%" },
];

const IMAGE_ALIGNMENT = [
    { icon: "oi-text-inline", value: "", title: _t("Inline") },
    { icon: "oi-text-wrap", value: "float-start", title: _t("Wrap text") },
    { icon: "oi-text-break", value: "d-block", title: _t("Break text") },
];

/**
 * @typedef { Object } ImageShared
 * @property { ImagePlugin['getTargetedImage'] } getTargetedImage
 * @property { ImagePlugin['previewImage'] } previewImage
 */

/**
 * @typedef {((img: HTMLImageElement) => void | true)[]} delete_image_overrides
 * @typedef {((img: HTMLImageElement) => boolean)[]} image_name_providers
 */

export class ImagePlugin extends Plugin {
    static id = "image";
    static dependencies = ["history", "dom", "selection"];
    static shared = ["getTargetedImage", "previewImage"];
    toolbarNamespace = "image";
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "deleteImage",
                description: _t("Remove (DELETE) image"),
                icon: "fa-trash text-danger",
                run: this.deleteImage.bind(this),
                isAvailable: isHtmlContentSupported,
            },
            {
                id: "previewImage",
                description: _t("Preview image"),
                icon: "fa-search-plus",
                run: this.previewImage.bind(this),
                isAvailable: isHtmlContentSupported,
            },
            {
                id: "resizeImage",
                run: this.resizeImage.bind(this),
                isAvailable: isHtmlContentSupported,
            },
        ],
        region_properties: { is: "IMG", toolbar: this.toolbarNamespace },
        toolbar_groups: [
            withSequence(26, { id: "image_modifiers", namespaces: ["image"] }),
            withSequence(26, { id: "image_size", namespaces: ["image"] }),
            withSequence(32, { id: "image_delete", namespaces: ["image"] }),
        ],
        toolbar_items: [
            {
                id: "image_preview",
                groupId: "image_actions",
                commandId: "previewImage",
            },
            {
                id: "image_alignment",
                description: _t("Set image alignment"),
                groupId: "image_modifiers",
                Component: ImageAlignSelector,
                props: {
                    items: IMAGE_ALIGNMENT,
                    getDisplay: () => this.imageAlignment,
                    focusEditable: () => this.dependencies.selection.focusEditable(),
                    onSelected: (item) => {
                        this.setImageAlignment(item);
                    },
                },
                isAvailable: isHtmlContentSupported,
            },
            {
                id: "image_padding",
                groupId: "image_modifiers",
                description: _t("Set image padding"),
                Component: ImageToolbarDropdown,
                props: {
                    name: "image_padding",
                    icon: "html_editor.ImagePaddingIcon",
                    items: IMAGE_PADDING,
                    focusEditable: () => this.dependencies.selection.focusEditable(),
                    onSelected: (item) => {
                        this.setImagePadding({ size: item.value });
                    },
                },
                isAvailable: isHtmlContentSupported,
            },
            {
                id: "image_size",
                groupId: "image_size",
                description: _t("Resize image"),
                Component: ImageToolbarDropdown,
                props: {
                    name: "image_size",
                    getDisplay: () => this.imageSize,
                    items: IMAGE_SIZE,
                    focusEditable: () => this.dependencies.selection.focusEditable(),
                    icon: "fa-expand",
                    onSelected: (item) => {
                        this.resizeImage({ size: item.value });
                        this.updateImageParams();
                    },
                },
                isAvailable: (selection) =>
                    isHtmlContentSupported(selection) && (this.config.allowImageResize ?? true),
            },
            {
                id: "image_delete",
                groupId: "image_delete",
                commandId: "deleteImage",
            },
        ],

        /** Handlers */
        on_selectionchange_handlers: withSequence(READ, this.updateImageParams.bind(this)),
        on_undone_handlers: this.updateImageParams.bind(this),
        on_redone_handlers: this.updateImageParams.bind(this),
        should_show_hint_predicates: (node) => {
            if (isElementOverlappingAnyFloatingImage(closestBlock(node))) {
                return false;
            }
        },

        /** Providers */
        paste_media_url_command_providers: this.getCommandForImageUrlPaste.bind(this),
    };

    setup() {
        this.imageSize = proxy({ displayName: "Default" });
        this.addDomListener(this.editable, "pointerdown", (e) => {
            const selection = this.dependencies.selection.getEditableSelection();
            if (selection.isCollapsed && e.target.tagName === "IMG") {
                this.setSelectionAroundImage(e.target);
            }
        });
        this.imageAlignment = proxy({ displayIcon: "oi-text-inline" });
        this.addDomListener(this.editable, "click", (e) => {
            if (e.target.tagName === "IMG") {
                this.setSelectionAroundImage(e.target);
            }
        });
        this.fileViewer = this.services.fileViewer();
    }

    destroy() {
        super.destroy();
    }

    get imageSizeName() {
        const targetedImg = this.getTargetedImage();
        if (!targetedImg) {
            return "Default";
        }
        return targetedImg.style.width || `${targetedImg.width}px`;
    }

    /**
     * @returns {string} icon class
     */
    get imageAlignmentIcon() {
        const targetedImg = this.getTargetedImage();
        if (targetedImg) {
            for (const { value, icon } of IMAGE_ALIGNMENT) {
                if (value && targetedImg.classList.contains(value)) {
                    return icon;
                }
            }
        }
        return "oi-text-inline";
    }

    setImageAlignment(alignment) {
        const targetedImg = this.getTargetedImage();
        if (!targetedImg) {
            return;
        }
        targetedImg.classList.remove(...IMAGE_ALIGNMENT.map(({ value }) => value).filter(Boolean));
        if (alignment.value) {
            targetedImg.classList.add(alignment.value);
        }
        this.imageAlignment.displayIcon = alignment.icon;
        this.dependencies.history.commit();
    }

    setImagePadding({ size } = {}) {
        const targetedImg = this.getTargetedImage();
        if (!targetedImg) {
            return;
        }
        for (const classString of targetedImg.classList) {
            if (classString.match(/^p-[0-9]$/)) {
                targetedImg.classList.remove(classString);
            }
        }
        targetedImg.classList.add(`p-${size}`);
        this.dependencies.history.commit();
    }
    resizeImage({ size } = {}) {
        const targetedImg = this.getTargetedImage();
        if (!targetedImg) {
            return;
        }
        targetedImg.style.width = size || "";
        this.dependencies.history.commit();
    }

    previewImage() {
        const targetedImg = this.getTargetedImage();
        if (!targetedImg) {
            return;
        }
        let imageName;
        // Keep the result from the first predicate that returns something.
        this.getResource("image_name_providers").find((p) => {
            imageName = p(targetedImg);
            return imageName;
        });
        const fileModel = {
            isImage: true,
            isViewable: true,
            name: imageName || targetedImg.src,
            defaultSource: targetedImg.src,
            downloadUrl: targetedImg.src,
        };
        this.document.getSelection().collapseToEnd();
        this.fileViewer.open(fileModel);
    }

    deleteImage() {
        const targetedImg = this.getTargetedImage();
        if (targetedImg) {
            if (this.delegateTo("delete_image_overrides", targetedImg)) {
                return;
            }
            const cursors = this.dependencies.selection.preserveSelection();
            cursors.update(callbacksForCursorUpdate.remove(targetedImg));
            const blockEl = closestBlock(targetedImg.parentElement);
            targetedImg.remove();
            cursors.restore();
            fillEmpty(blockEl);
            this.dependencies.history.commit();
        }
    }

    getTargetedImage() {
        const targetedNodes = this.dependencies.selection.getTargetedNodes();
        return targetedNodes.find((node) => node.tagName === "IMG");
    }

    hasImageSize(size) {
        const targetedImg = this.getTargetedImage();
        return targetedImg?.style?.width === size;
    }

    isSelectionShaped(shape) {
        const targetedNodes = this.dependencies.selection
            .getTargetedNodes()
            .filter((n) => n.tagName === "IMG" && n.classList.contains(shape));
        return targetedNodes.length > 0;
    }

    /**
     * @param {string} url
     */
    getCommandForImageUrlPaste(url) {
        if (isImageUrl(url)) {
            return {
                title: _t("Embed Image"),
                description: _t("Embed the image in the document."),
                icon: "fa-image",
                run: () => {
                    this.trigger(
                        "on_will_paste_handlers",
                        this.dependencies.selection.getEditableSelection()
                    );
                    const img = this.document.createElement("IMG");
                    img.setAttribute("src", url);
                    this.dependencies.dom.insert(img);
                    this.dependencies.history.commit();
                },
            };
        }
    }

    updateImageParams() {
        this.imageSize.displayName = this.imageSizeName;
        this.imageAlignment.displayIcon = this.imageAlignmentIcon;
    }

    setSelectionAroundImage(img) {
        const [anchorNode, anchorOffset, focusNode, focusOffset] = boundariesOut(img);
        this.dependencies.selection.setSelection({
            anchorNode,
            anchorOffset,
            focusNode,
            focusOffset,
        });
        this.dependencies.selection.focusEditable();
    }
}
