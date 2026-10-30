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

const IMAGE_PADDING_CLASS_REGEX = /^p-[0-9]$/;

const IMAGE_SIZE = [
    { name: _t("Default"), value: "" },
    { name: _t("100%"), value: "100%" },
    { name: _t("50%"), value: "50%" },
    { name: _t("25%"), value: "25%" },
];

const IMAGE_ALIGNMENT = [
    { icon: "format_image_inline_left", value: "", title: _t("Inline") },
    { icon: "format_image_left", value: "float-start", title: _t("Wrap text") },
    { icon: "format_image_front", value: "d-block", title: _t("Break text") },
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
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "deleteImage",
                description: _t("Remove (DELETE) image"),
                icon: "delete",
                iconClass: "oi-filled text-danger",
                run: this.deleteImage.bind(this),
                isAvailable: isHtmlContentSupported,
            },
            {
                id: "previewImage",
                description: _t("Preview image"),
                icon: "zoom_in",
                run: this.previewImage.bind(this),
                isAvailable: isHtmlContentSupported,
            },
            {
                id: "resizeImage",
                run: this.resizeImage.bind(this),
                isAvailable: isHtmlContentSupported,
            },
        ],
        properties: [
            {
                predicate: "IMG",
                toolbar: "image",
                // Clicking an image selects it rather than putting a cursor next to it.
                selectableOnClick: true,
            },
        ],
        toolbar_groups: [
            withSequence(26, { id: "image_modifiers", namespaces: ["image"] }),
            withSequence(28, { id: "image_actions", namespaces: ["image"] }),
            withSequence(34, { id: "image_delete", namespaces: ["image"] }),
        ],
        toolbar_items: [
            withSequence(10, {
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
            }),
            withSequence(30, {
                id: "image_padding",
                groupId: "image_modifiers",
                description: _t("Set image padding"),
                Component: ImageToolbarDropdown,
                props: {
                    name: "image_padding",
                    icon: "padding",
                    getDisplay: () => this.imagePadding,
                    items: IMAGE_PADDING,
                    focusEditable: () => this.dependencies.selection.focusEditable(),
                    onSelected: (item) => {
                        this.setImagePadding({ size: item.value });
                    },
                },
                isAvailable: isHtmlContentSupported,
            }),
            {
                id: "image_size",
                groupId: "image_actions",
                description: _t("Resize image"),
                Component: ImageToolbarDropdown,
                props: {
                    name: "image_size",
                    getDisplay: () => this.imageSize,
                    items: IMAGE_SIZE,
                    focusEditable: () => this.dependencies.selection.focusEditable(),
                    icon: "resize",
                    onSelected: (item) => {
                        this.resizeImage({ size: item.value });
                        this.updateImageParams();
                    },
                },
                isAvailable: (selection) =>
                    isHtmlContentSupported(selection) && (this.config.allowImageResize ?? true),
            },
            {
                id: "image_preview",
                groupId: "image_actions",
                commandId: "previewImage",
                opensUi: true,
            },
            {
                id: "image_delete",
                groupId: "image_delete",
                commandId: "deleteImage",
            },
        ],

        /** Handlers */
        on_selectionchange_handlers: withSequence(READ, this.updateImageParams.bind(this)),
        on_history_commit_undone_handlers: this.updateImageParams.bind(this),
        on_history_commit_redone_handlers: this.updateImageParams.bind(this),
        should_show_hint_predicates: (node) => {
            if (isElementOverlappingAnyFloatingImage(closestBlock(node))) {
                return false;
            }
        },

        /** Providers */
        paste_media_url_command_providers: this.getCommandForImageUrlPaste.bind(this),
        on_editor_started_handlers: withSequence(0, this.moveSizeAttributesToStyle.bind(this)),
    };

    setup() {
        this.imageSize = proxy({ displayName: "Default", value: "" });
        this.imagePadding = proxy({ value: 0 });
        this.addDomListener(this.editable, "pointerdown", (e) => {
            const selection = this.dependencies.selection.getEditableSelection();
            if (selection.isCollapsed && e.target.tagName === "IMG") {
                this.setSelectionAroundImage(e.target);
            }
        });
        this.imageAlignment = proxy({ displayIcon: "format_image_inline_left" });
        this.fileViewer = this.services.fileViewer();
    }

    moveSizeAttributesToStyle() {
        // During `convert_inline`, image elements may receive `width` and `height` attributes,
        // along with inline styles. These attributes force specific dimensions, which breaks
        // the fallback to default sizing. We remove them here to allow proper resizing behavior.
        // The attributes will be re-applied on save.
        for (const img of this.editable.querySelectorAll("img[width], img[height]")) {
            const width = img.getAttribute("width");
            const height = img.getAttribute("height");
            img.removeAttribute("height");
            img.removeAttribute("width");
            img.style.setProperty("width", isNaN(width) ? width : `${width}px`);
            img.style.setProperty("height", isNaN(height) ? height : `${height}px`);
        }
    }

    destroy() {
        super.destroy();
    }

    /**
     * @param {HTMLImageElement} [targetedImg]
     */
    getImageSize(targetedImg) {
        if (!targetedImg) {
            return { displayName: "Default", value: "" };
        }
        return {
            displayName: targetedImg.style.width || `${targetedImg.width}px`,
            value: targetedImg.style.width,
        };
    }

    /**
     * @param {HTMLImageElement} [targetedImg]
     * @returns {number} padding size of the `p-N` class, 0 if none
     */
    getImagePadding(targetedImg) {
        const paddingClass = [...(targetedImg?.classList || [])].find((c) =>
            IMAGE_PADDING_CLASS_REGEX.test(c)
        );
        return paddingClass ? Number(paddingClass.slice(-1)) : 0;
    }

    /**
     * @param {HTMLImageElement} [targetedImg]
     * @returns {string} icon class
     */
    getImageAlignmentIcon(targetedImg) {
        if (targetedImg) {
            for (const { value, icon } of IMAGE_ALIGNMENT) {
                if (value && targetedImg.classList.contains(value)) {
                    return icon;
                }
            }
        }
        return "format_image_inline_left";
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
            if (IMAGE_PADDING_CLASS_REGEX.test(classString)) {
                targetedImg.classList.remove(classString);
            }
        }
        targetedImg.classList.add(`p-${size}`);
        this.imagePadding.value = size;
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
        this.document.activeElement.blur();
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

    /**
     * @param {string} url
     */
    getCommandForImageUrlPaste(url) {
        if (isImageUrl(url)) {
            return {
                title: _t("Embed Image"),
                description: _t("Embed the image in the document."),
                icon: "image",
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
        const targetedImg = this.getTargetedImage();
        Object.assign(this.imageSize, this.getImageSize(targetedImg));
        this.imagePadding.value = this.getImagePadding(targetedImg);
        this.imageAlignment.displayIcon = this.getImageAlignmentIcon(targetedImg);
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
