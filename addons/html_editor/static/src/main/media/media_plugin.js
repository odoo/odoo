import { Plugin } from "@html_editor/plugin";
import {
    ICON_SELECTOR,
    EDITABLE_MEDIA_CLASS,
    isIconElement,
    isMediaElement,
    isProtected,
    isProtecting,
} from "@html_editor/utils/dom_info";
import { backgroundImageCssToParts, backgroundImagePartsToCss } from "@html_editor/utils/image";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { MediaDialog } from "./media_dialog/media_dialog";
import { rightPos } from "@html_editor/utils/position";
import { withSequence } from "@html_editor/utils/resource";

const MEDIA_SELECTOR = `${ICON_SELECTOR} , .o_image, .media_iframe_video`;

/**
 * @typedef { Object } MediaShared
 * @property { MediaPlugin['savePendingImages'] } savePendingImages
 */

export class MediaPlugin extends Plugin {
    static id = "media";
    static dependencies = ["selection", "history", "dom", "dialog"];
    static shared = ["savePendingImages"];
    resources = {
        user_commands: [
            {
                id: "replaceImage",
                title: _t("Replace media"),
                run: this.replaceImage.bind(this),
            },
            {
                id: "insertMedia",
                title: _t("Media"),
                description: _t("Insert image or icon"),
                keywords: [_t("Image"), _t("Icon")],
                icon: "fa-file-image-o",
                run: this.openMediaDialog.bind(this),
            },
        ],
        toolbar_groups: withSequence(29, {
            id: "replace_image",
            namespace: "image",
        }),
        toolbar_items: [
            {
                id: "replace_image",
                groupId: "replace_image",
                commandId: "replaceImage",
                text: "Replace",
            },
        ],
        powerbox_categories: withSequence(40, { id: "media", name: _t("Media") }),
        powerbox_items: [
            ...(this.config.disableImage
                ? []
                : [{ categoryId: "media", commandId: "insertMedia" }]),
        ],
        power_buttons: withSequence(1, { commandId: "insertMedia" }),

        /** Handlers */
        clean_handlers: this.clean.bind(this),
        clean_for_save_handlers: ({ root }) => this.cleanForSave(root),
        normalize_handlers: this.normalizeMedia.bind(this),

        unsplittable_node_predicates: isIconElement, // avoid merge
        functional_empty_node_predicates: isMediaElement,
        is_node_editable_predicates: this.isEditableMediaElement.bind(this),

        selectors_for_feff_providers: () => ICON_SELECTOR,
    };

    get recordInfo() {
        return this.config.getRecordInfo ? this.config.getRecordInfo() : {};
    }

    isEditableMediaElement(node) {
        return (
            (isMediaElement(node) || node.nodeName === "IMG") &&
            node.classList.contains(EDITABLE_MEDIA_CLASS)
        );
    }

    replaceImage() {
        const targetedNodes = this.dependencies.selection.getTargetedNodes();
        const node = targetedNodes.find((node) => node.tagName === "IMG");
        if (node) {
            this.openMediaDialog({ node });
            this.dependencies.history.addStep();
        }
    }

    normalizeMedia(node) {
        const mediaElements = [...node.querySelectorAll(MEDIA_SELECTOR)];
        if (node.matches(MEDIA_SELECTOR)) {
            mediaElements.push(node);
        }
        for (const el of mediaElements) {
            if (isProtected(el) || isProtecting(el)) {
                continue;
            }
            el.setAttribute(
                "contenteditable",
                el.hasAttribute("contenteditable") ? el.getAttribute("contenteditable") : "false"
            );
            if (isIconElement(el)) {
                el.textContent = "\u200B";
            }
        }
    }

    clean(root) {
        for (const el of root.querySelectorAll(MEDIA_SELECTOR)) {
            if (isIconElement(el)) {
                el.textContent = "";
            }
        }
    }

    cleanForSave(root) {
        for (const el of root.querySelectorAll(MEDIA_SELECTOR)) {
            if (isIconElement(el)) {
                el.textContent = "";
            }
            el.removeAttribute("contenteditable");
        }
    }

    onSaveMediaDialog(element, { node }) {
        if (!element) {
            // @todo @phoenix to remove
            throw new Error("Element is required: onSaveMediaDialog");
            // return;
        }

        if (node) {
            const changedIcon = isIconElement(node) && isIconElement(element);
            if (changedIcon) {
                // Preserve tag name when changing an icon and not recreate the
                // editors unnecessarily.
                for (const attribute of element.attributes) {
                    node.setAttribute(attribute.nodeName, attribute.nodeValue);
                }
            } else {
                node.replaceWith(element);
            }
        } else {
            this.dependencies.dom.insert(element);
        }
        // Collapse selection after the inserted/replaced element.
        const [anchorNode, anchorOffset] = rightPos(element);
        this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
        this.dependencies.history.addStep();
    }

    openMediaDialog(params = {}) {
        const { resModel, resId, field, type } = this.recordInfo;
        const mediaDialogClosedPromise = this.dependencies.dialog.addDialog(MediaDialog, {
            resModel,
            resId,
            useMediaLibrary: !!(
                field &&
                ((resModel === "ir.ui.view" && field === "arch") || type === "html")
            ), // @todo @phoenix: should be removed and moved to config.mediaModalParams
            media: params.node,
            save: (element) => {
                this.onSaveMediaDialog(element, { node: params.node });
            },
            onAttachmentChange: this.config.onAttachmentChange || (() => {}),
            noVideos: !!this.config.disableVideo,
            noImages: !!this.config.disableImage,
            extraTabs: this.getResource("media_dialog_extra_tabs"),
            ...this.config.mediaModalParams,
            ...params,
        });
        return mediaDialogClosedPromise;
    }

    async savePendingImages() {
        const editableEl = this.editable;
        const { resModel, resId } = this.recordInfo;
        // When saving a webp, o_b64_image_to_save is turned into
        // o_modified_image_to_save by saveB64Image to request the saving
        // of the pre-converted webp resizes and all the equivalent jpgs.
        const b64Proms = [...editableEl.querySelectorAll(".o_b64_image_to_save")].map(
            async (el) => {
                const dirtyEditable = el.closest(".o_dirty");
                if (dirtyEditable && dirtyEditable !== editableEl) {
                    // Do nothing as there is an editable element closer to the
                    // image that will perform the `saveB64Image()` call with
                    // the correct "resModel" and "resId" parameters.
                    return;
                }
                await this.saveB64Image(el, resModel, resId);
            }
        );
        const modifiedProms = [...editableEl.querySelectorAll(".o_modified_image_to_save")].map(
            async (el) => {
                const dirtyEditable = el.closest(".o_dirty");
                if (dirtyEditable && dirtyEditable !== editableEl) {
                    // Do nothing as there is an editable element closer to the
                    // image that will perform the `saveModifiedImage()` call
                    // with the correct "resModel" and "resId" parameters.
                    return;
                }
                await this.saveModifiedImage(el, resModel, resId);
            }
        );
        const proms = [...b64Proms, ...modifiedProms];
        const hasChange = !!proms.length;
        if (hasChange) {
            await Promise.all(proms);
        }
        return hasChange;
    }

    createAttachment({ el, imageData, resModel, resId }) {
        return rpc("/html_editor/attachment/add_data", {
            name: el.dataset.fileName || "",
            data: imageData,
            is_image: true,
            res_model: resModel,
            res_id: resId,
        });
    }

    /**
     * Saves a base64 encoded image as an attachment.
     * Relies on saveModifiedImage being called after it for webp.
     *
     * @private
     * @param {Element} el
     * @param {string} resModel
     * @param {number} resId
     */
    async saveB64Image(el, resModel, resId) {
        const imageData = el.getAttribute("src").split("base64,")[1];
        if (!imageData) {
            // Checks if the image is in base64 format for RPC call. Relying
            // only on the presence of the class "o_b64_image_to_save" is not
            // robust enough.
            el.classList.remove("o_b64_image_to_save");
            return;
        }
        const attachment = await this.createAttachment({
            el,
            imageData,
            resId,
            resModel,
        });
        if (!attachment) {
            return;
        }
        if (attachment.mimetype === "image/webp") {
            el.classList.add("o_modified_image_to_save");
            el.dataset.originalId = attachment.id;
            el.dataset.mimetype = attachment.mimetype;
            el.dataset.fileName = attachment.name;
            return this.saveModifiedImage(el, resModel, resId);
        } else {
            let src = attachment.image_src;
            if (!attachment.public) {
                let accessToken = attachment.access_token;
                if (!accessToken) {
                    [accessToken] = await this.services.orm.call(
                        "ir.attachment",
                        "generate_access_token",
                        [attachment.id]
                    );
                }
                src += `?access_token=${encodeURIComponent(accessToken)}`;
            }
            el.setAttribute("src", src);
        }
        el.classList.remove("o_b64_image_to_save");
    }

    /**
     * Saves a modified image as an attachment.
     *
     * @private
     * @param {Element} el
     * @param {string} resModel
     * @param {number} resId
     */
    async saveModifiedImage(el, resModel, resId) {
        const isBackground = !el.matches("img");
        // Modifying an image always creates a copy of the original, even if
        // it was modified previously, as the other modified image may be used
        // elsewhere if the snippet was duplicated or was saved as a custom one.
        let altData = undefined;
        const isImageField = !!el.closest("[data-oe-type=image]");
        if (el.dataset.mimetype === "image/webp" && isImageField) {
            // Generate alternate sizes and format for reports.
            altData = {};
            const image = document.createElement("img");
            image.src = isBackground ? el.dataset.bgSrc : el.getAttribute("src");
            await new Promise((resolve) => image.addEventListener("load", resolve));
            const originalSize = Math.max(image.width, image.height);
            const smallerSizes = [1024, 512, 256, 128].filter((size) => size < originalSize);
            for (const size of [originalSize, ...smallerSizes]) {
                const ratio = size / originalSize;
                const canvas = document.createElement("canvas");
                canvas.width = image.width * ratio;
                canvas.height = image.height * ratio;
                const ctx = canvas.getContext("2d");
                ctx.fillStyle = "rgb(255, 255, 255)";
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(
                    image,
                    0,
                    0,
                    image.width,
                    image.height,
                    0,
                    0,
                    canvas.width,
                    canvas.height
                );
                altData[size] = {
                    "image/jpeg": canvas.toDataURL("image/jpeg", 0.75).split(",")[1],
                };
                if (size !== originalSize) {
                    altData[size]["image/webp"] = canvas
                        .toDataURL("image/webp", 0.75)
                        .split(",")[1];
                }
            }
        }
        const newAttachmentSrc = await rpc(
            `/html_editor/modify_image/${encodeURIComponent(el.dataset.originalId)}`,
            {
                res_model: resModel,
                res_id: parseInt(resId),
                data: (isBackground ? el.dataset.bgSrc : el.getAttribute("src")).split(",")[1],
                alt_data: altData,
                mimetype: isBackground
                    ? el.dataset.mimetype
                    : el.getAttribute("src").split(":")[1].split(";")[0],
                name: el.dataset.fileName ? el.dataset.fileName : null,
            }
        );
        el.classList.remove("o_modified_image_to_save");
        if (isBackground) {
            const parts = backgroundImageCssToParts(el.style["background-image"]);
            parts.url = `url('${newAttachmentSrc}')`;
            const combined = backgroundImagePartsToCss(parts);
            el.style["background-image"] = combined;
            delete el.dataset.bgSrc;
        } else {
            el.setAttribute("src", newAttachmentSrc);
        }
    }
}
