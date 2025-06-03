import { Plugin } from "@html_editor/plugin";
import {
    ICON_SELECTOR,
    MEDIA_SELECTOR,
    EDITABLE_MEDIA_CLASS,
    isIconElement,
    isMediaElement,
    isProtected,
    isProtecting,
} from "@html_editor/utils/dom_info";
import {
    backgroundImageCssToParts,
    backgroundImagePartsToCss,
    getImageSrc,
} from "@html_editor/utils/image";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { MediaDialog } from "./media_dialog/media_dialog";
import { rightPos } from "@html_editor/utils/position";
import { withSequence } from "@html_editor/utils/resource";
import { closestElement } from "@html_editor/utils/dom_traversal";

/**
 * @typedef { Object } MediaShared
 * @property { MediaPlugin['savePendingImages'] } savePendingImages
 */

export class MediaPlugin extends Plugin {
    static id = "media";
    static dependencies = ["selection", "history", "dom", "dialog"];
    static shared = ["savePendingImages", "openMediaDialog"];
    static defaultConfig = {
        allowImage: true,
        allowMediaDialogVideo: true,
    };
    resources = {
        user_commands: [
            {
                id: "replaceImage",
                description: _t("Replace media"),
                icon: "fa-exchange",
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
        toolbar_groups: withSequence(31, { id: "replace_image", namespaces: ["image"] }),
        toolbar_items: [
            {
                id: "replace_image",
                groupId: "replace_image",
                commandId: "replaceImage",
            },
        ],
        powerbox_categories: withSequence(40, { id: "media", name: _t("Media") }),
        powerbox_items: [
            ...(this.config.allowImage ? [{ categoryId: "media", commandId: "insertMedia" }] : []),
        ],
        power_buttons: withSequence(1, { commandId: "insertMedia" }),

        /** Handlers */
        clean_for_save_handlers: ({ root }) => this.cleanForSave(root),
        normalize_handlers: this.normalizeMedia.bind(this),
        selectionchange_handlers: this.selectAroundIcon.bind(this),

        unsplittable_node_predicates: isIconElement, // avoid merge
        is_node_editable_predicates: this.isEditableMediaElement.bind(this),
        clipboard_content_processors: this.clean.bind(this),
        clipboard_text_processors: (text) => text.replace(/\u200B/g, ""),

        selectors_for_feff_providers: () => ICON_SELECTOR,
        before_save_handlers: this.savePendingImages.bind(this),
    };

    getRecordInfo(editableEl = null) {
        return this.config.getRecordInfo ? this.config.getRecordInfo(editableEl) : {};
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
            // Do not update the text if it's already OK to avoid recording a
            // mutation on Firefox. (Chrome filters them out.)
            if (isIconElement(el) && el.textContent !== "\u200B") {
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

    async onSaveMediaDialog(element, { node }) {
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
                element = node;
            } else {
                node.replaceWith(element);
            }
        } else {
            this.dependencies.dom.insert(element);
        }
        // Collapse selection after the inserted/replaced element.
        const [anchorNode, anchorOffset] = rightPos(element);
        this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
        this.dispatchTo("after_save_media_dialog_handlers", element);
        this.dependencies.history.addStep();
    }

    openMediaDialog(params = {}, editableEl = null) {
        const oldSave =
            params.save || ((element) => this.onSaveMediaDialog(element, { node: params.node }));
        params.save = async (...args) => {
            const selection = args[0];
            const elements = selection
                ? selection[Symbol.iterator]
                    ? selection
                    : [selection]
                : [];
            for (const onMediaDialogSaved of this.getResource("on_media_dialog_saved_handlers")) {
                await onMediaDialogSaved(elements, { node: params.node });
            }
            return oldSave(...args);
        };
        const { resModel, resId, field, type } = this.getRecordInfo(editableEl);
        const mediaDialogClosedPromise = this.dependencies.dialog.addDialog(MediaDialog, {
            resModel,
            resId,
            useMediaLibrary: !!(
                field &&
                ((resModel === "ir.ui.view" && field === "arch") || type === "html")
            ), // @todo @phoenix: should be removed and moved to config.mediaModalParams
            media: params.node,
            onAttachmentChange: this.config.onAttachmentChange || (() => {}),
            noVideos: !this.config.allowMediaDialogVideo,
            noImages: !this.config.allowImage,
            extraTabs: this.getResource("media_dialog_extra_tabs").filter(
                (tab) => !(tab.id === "DOCUMENTS" && params.noDocuments)
            ),
            vimeoPreviewIds: [
                "528686125",
                "430330731",
                "509869821",
                "397142251",
                "763851966",
                "486931161",
                "499761556",
                "392935303",
                "728584384",
                "865314310",
                "511727912",
                "466830211",
            ],
            ...this.config.mediaModalParams,
            ...params,
        });
        return mediaDialogClosedPromise;
    }

    async savePendingImages(editableEl = this.editable) {
        const { resModel, resId } = this.getRecordInfo(editableEl);
        // When saving a webp, o_b64_image_to_save is turned into
        // o_modified_image_to_save by saveB64Image to request the saving
        // of the pre-converted webp resizes and all the equivalent jpgs.
        const b64Proms = [...editableEl.querySelectorAll(".o_b64_image_to_save")].map(
            async (el) => {
                await this.saveB64Image(el, resModel, resId);
            }
        );
        const modifiedProms = [...editableEl.querySelectorAll(".o_modified_image_to_save")].map(
            async (el) => {
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
            image.src = getImageSrc(el);
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
                data: getImageSrc(el).split(",")[1],
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
        } else {
            el.setAttribute("src", newAttachmentSrc);
        }
    }

    /**
     * @param {import("@html_editor/core/selection_plugin").SelectionData} param0
     */
    selectAroundIcon({ editableSelection: { anchorNode, isCollapsed } }) {
        if (isCollapsed && closestElement(anchorNode, isIconElement)) {
            this.dependencies.selection.selectAroundNonEditable();
        }
    }
}
