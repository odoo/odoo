import { Plugin } from "@html_editor/plugin";
import {
    ICON_SELECTOR,
    isIconElement,
    isProtected,
    isProtecting,
} from "@html_editor/utils/dom_info";
import { backgroundImageCssToParts, backgroundImagePartsToCss } from "@html_editor/utils/image";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { MediaDialog } from "./media_dialog/media_dialog";

const MEDIA_SELECTOR = `${ICON_SELECTOR} , .o_image, .media_iframe_video`;

export class MediaPlugin extends Plugin {
    static name = "media";
    static dependencies = ["selection", "history", "dom"];
    static shared = ["savePendingImages"];
    /** @type { (p: MediaPlugin) => Record<string, any> } */
    static resources = (p) => {
        const powerboxItems = [];
        if (!p.config.disableImage) {
            powerboxItems.push({
                name: _t("Image"),
                description: _t("Insert an image"),
                category: "media",
                fontawesome: "fa-file-image-o",
                action(dispatch) {
                    dispatch("INSERT_MEDIA");
                },
            });
        }
        if (!p.config.disableVideo) {
            powerboxItems.push({
                name: _t("Video"),
                description: _t("Insert a video"),
                category: "media",
                fontawesome: "fa-file-video-o",
                action(dispatch) {
                    dispatch("INSERT_MEDIA", {
                        noVideos: false,
                        noImages: true,
                        noIcons: true,
                        noDocuments: true,
                    });
                },
            });
        }
        const resources = {
            powerboxCategory: { id: "media", name: _t("Media"), sequence: 40 },
            powerboxItems,
            toolbarCategory: { id: "replace_image", sequence: 29, namespace: "image" },
            toolbarItems: [
                {
                    id: "replace_image",
                    category: "replace_image",
                    action(dispatch) {
                        dispatch("REPLACE_IMAGE");
                    },
                    name: "Replace media",
                    text: "Replace",
                },
            ],
        };
        return resources;
    };

    get recordInfo() {
        return this.config.getRecordInfo ? this.config.getRecordInfo() : {};
    }

    handleCommand(command, payload) {
        switch (command) {
            case "NORMALIZE":
                this.normalizeMedia(payload.node);
                break;
            case "CLEAN":
                // TODO @phoenix: evaluate if this should be cleanforsave instead
                this.clean(payload.root);
                break;
            case "CLEAN_FOR_SAVE":
                this.cleanForSave(payload.root);
                break;
            case "INSERT_MEDIA":
                this.openMediaDialog(payload);
                break;
            case "REPLACE_IMAGE": {
                const selectedNodes = this.shared.getSelectedNodes();
                const node = selectedNodes.find((node) => node.tagName === "IMG");
                if (node) {
                    this.openMediaDialog({ node });
                    this.dispatch("ADD_STEP");
                }
                break;
            }
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
            el.removeAttribute("contenteditable");
        }
    }

    onSaveMediaDialog(element, { node, restoreSelection }) {
        restoreSelection();
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
            this.shared.domInsert(element);
        }
        this.dispatch("ADD_STEP");
    }

    openMediaDialog(params = {}) {
        const selection = this.shared.getEditableSelection();
        const restoreSelection = () => {
            this.shared.setSelection(selection);
        };
        const { resModel, resId, field, type } = this.recordInfo;
        this.services.dialog.add(MediaDialog, {
            resModel,
            resId,
            useMediaLibrary: !!(
                field &&
                ((resModel === "ir.ui.view" && field === "arch") || type === "html")
            ), // @todo @phoenix: should be removed and moved to config.mediaModalParams
            media: params.node,
            save: (element) => {
                this.onSaveMediaDialog(element, { node: params.node, restoreSelection });
            },
            close: restoreSelection,
            onAttachmentChange: this.config.onAttachmentChange || (() => {}),
            noVideos: !!this.config.disableVideo,
            noImages: !!this.config.disableImage,
            ...this.config.mediaModalParams,
            ...params,
        });
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
