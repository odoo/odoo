/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { AttachmentError } from "@web_editor/components/media_dialog/file_selector";
import { AttachmentError as HtmlAttachmentError } from "@html_editor/main/media/media_dialog/file_selector";
import { AutoResizeImage } from "@web_editor/components/media_dialog/image_selector";
import { AutoResizeImage as HtmlAutoResizeImage } from "@html_editor/main/media/media_dialog/image_selector";
import { removeOnImageChangeAttrs } from "@web_editor/js/common/utils";
import { Component, useRef } from "@odoo/owl";

class ImageMediaRemoveDialog extends Component {
    static template = "website.ImageMediaRemoveDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        confirm: Function,
        title: String,
    };
    setup() {
        this.website = useService("website");
        this.deleteFromWebsiteRef = useRef("deleteFromWebsite");
    }
    async onClickConfirm() {
        await this.props.confirm(this.deleteFromWebsiteRef.el, this.website);
        this.props.close();
    }
}

patch(AutoResizeImage.prototype, {
    /**
     * @override
     */
    async remove() {
        const mediaAndCopies = await this.props.getOriginalAndCopies(this.props.id);
        const ids = mediaAndCopies.attachmentsIds;
        // True if the media can be used on website pages.
        const canHideMedia = mediaAndCopies.res_model === "ir.ui.view"
            && mediaAndCopies.res_id === 0;
        this.dialogs.add(ImageMediaRemoveDialog, {
            title: _t("Confirmation"),
            canHideMedia: canHideMedia,
            confirm: async (deleteFromWebsiteCheckboxEl, website) => {
                const prevented = await rpc("/web_editor/attachment/remove", {
                    ids,
                    keep_on_website: !!deleteFromWebsiteCheckboxEl
                        && !deleteFromWebsiteCheckboxEl.checked,
                });
                if (Object.keys(prevented).length) {
                    this.dialogs.add(AttachmentError, {
                        views: ids.map(id => prevented[id]),
                    });
                    return;
                }
                // Remove the images from the media dialog.
                this.props.onRemoved(this.props.id);
                // Remove the images from the current page.
                if (!website.pageDocument || !deleteFromWebsiteCheckboxEl?.checked) {
                    return;
                }
                const imagePlaceholder = "/web/image/web.image_placeholder";
                const dataAttrsToRemove = [
                    ...removeOnImageChangeAttrs,
                    "fileName", "originalMimetype",
                ];
                ids.forEach(id => {
                    const onCurrentPageImgEls = website.pageDocument.querySelectorAll(
                        `[data-original-id='${id}'], [style*="/web/image/${id}"]`
                    );
                    for (const onCurrentPageImgEl of onCurrentPageImgEls) {
                        delete onCurrentPageImgEl.alt;
                        onCurrentPageImgEl.classList.remove(
                            "o_modified_image_to_save",
                            "o_we_custom_image"
                        );
                        dataAttrsToRemove.forEach(attr => delete onCurrentPageImgEl.dataset[attr]);

                        if (onCurrentPageImgEl.nodeName === "IMG") {
                            onCurrentPageImgEl.src = imagePlaceholder;
                            continue;
                        }
                        onCurrentPageImgEl.style.backgroundImage = `url(${imagePlaceholder})`;
                        if (onCurrentPageImgEl.classList.contains("o_record_cover_image")) {
                            onCurrentPageImgEl.closest(".o_record_cover_container")
                                .dataset.coverClass = "";
                        } else {
                            $(onCurrentPageImgEl).trigger("background_changed", false);
                        }
                    }
                });
            },
        });
    }
});

patch(HtmlAutoResizeImage.prototype, {
    /**
     * @override
     */
    async remove() {
        const mediaAndCopies = await this.props.getOriginalAndCopies(this.props.id);
        const ids = mediaAndCopies.attachmentsIds;
        // True if the media can be used on website pages.
        const canHideMedia = mediaAndCopies.res_model === "ir.ui.view"
            && mediaAndCopies.res_id === 0;
        this.dialogs.add(ImageMediaRemoveDialog, {
            title: _t("Confirmation"),
            canHideMedia: canHideMedia,
            confirm: async (deleteFromWebsiteCheckboxEl, website) => {
                const prevented = await rpc("/web_editor/attachment/remove", {
                    ids,
                    keep_on_website: !!deleteFromWebsiteCheckboxEl
                        && !deleteFromWebsiteCheckboxEl.checked,
                });
                if (Object.keys(prevented).length) {
                    this.dialogs.add(HtmlAttachmentError, {
                        views: ids.map(id => prevented[id]),
                    });
                    return;
                }
                // Remove the images from the media dialog.
                this.props.onRemoved(this.props.id);
                // Remove the images from the current page.
                if (!website.pageDocument || !deleteFromWebsiteCheckboxEl?.checked) {
                    return;
                }
                const imagePlaceholder = "/web/image/web.image_placeholder";
                const dataAttrsToRemove = [
                    ...removeOnImageChangeAttrs,
                    "fileName", "originalMimetype",
                ];
                ids.forEach(id => {
                    const onCurrentPageImgEls = website.pageDocument.querySelectorAll(
                        `[data-original-id='${id}'], [style*="/web/image/${id}"]`
                    );
                    for (const onCurrentPageImgEl of onCurrentPageImgEls) {
                        delete onCurrentPageImgEl.alt;
                        onCurrentPageImgEl.classList.remove(
                            "o_modified_image_to_save",
                            "o_we_custom_image"
                        );
                        dataAttrsToRemove.forEach(attr => delete onCurrentPageImgEl.dataset[attr]);

                        if (onCurrentPageImgEl.nodeName === "IMG") {
                            onCurrentPageImgEl.src = imagePlaceholder;
                            continue;
                        }
                        onCurrentPageImgEl.style.backgroundImage = `url(${imagePlaceholder})`;
                        if (onCurrentPageImgEl.classList.contains("o_record_cover_image")) {
                            onCurrentPageImgEl.closest(".o_record_cover_container")
                                .dataset.coverClass = "";
                        } else {
                            $(onCurrentPageImgEl).trigger("background_changed", false);
                        }
                    }
                });
            },
        });
    }
});
