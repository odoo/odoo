odoo.define('website.widgets.media', function (require) {
'use strict';

const { _t } = require('web.core');
const { removeOnImageChangeAttrs } = require('web_editor.image_processing');
const {ImageWidget} = require('wysiwyg.widgets.media');

ImageWidget.include({
    _getAttachmentsDomain() {
        const domain = this._super(...arguments);
        domain.push(
            '|', ['url', '=', false],
            '!', ['url', '=like', '/web/image/website.%'],
            "!", ["res_id", "=", -1]
        );
        domain.push(['key', '=', false]);
        return domain;
    },
    /**
     * @override
     */
    _getRemoveDialogOptions(ev) {
        const self = this;
        return {
            buttons: [
                {
                    text: _t("Ok"),
                    classes: "btn-primary",
                    click: () => {
                        self._removeAttachment(ev, { remove_optimized: true, keep_on_website: true });
                    },
                    close: true,
                }, {
                    text: _t("Delete from all website pages"),
                    click: () => {
                        self._removeAttachment(ev, { remove_optimized: true, keep_on_website: false }, self._removeFromCurrentPage);
                    },
                    close: true,
                }, {
                    text: _t("Cancel"),
                    close: true,
                },
            ],
        };
    },
    _removeFromCurrentPage(attachments) {
        // Looking for saved attachments, or for attachments that have not yet
        // been saved, are therefore temporarily stored in base64, and have not
        // been optimized yet.
        attachments.forEach(attachment => {
            const onCurrentPageImgEls = document.querySelector("#wrapwrap")
                .querySelectorAll(
                    `[style*='${attachment.image_src}'],
                    [src*='${attachment.image_src}'],
                    [data-original-id='${attachment.id}']:is([src*='base64'], [style*='base64'])`
                );
            if (!onCurrentPageImgEls) {
                return;
            }
            for (const onCurrentPageImgEl of onCurrentPageImgEls) {
                const attrsToRemove =  [
                    ...removeOnImageChangeAttrs,
                    "bgSrc", "fileName", "originalMimetype", "shape", "shapeColors",
                ];
                if (onCurrentPageImgEl.nodeName === "IMG") {
                    const newImgEl = onCurrentPageImgEl.cloneNode(true);
                    attrsToRemove.forEach(attr => delete newImgEl.dataset[attr]);
                    delete newImgEl.alt;
                    newImgEl.src = "/web/image/website.s_image_text_default_image";
                    onCurrentPageImgEl.insertAdjacentElement("afterend", newImgEl);
                    onCurrentPageImgEl.remove();
                } else if (onCurrentPageImgEl.classList.contains("s_parallax_bg")) {
                    onCurrentPageImgEl.parentElement.classList
                        .remove("parallax", "s_parallax_is_fixed");
                    onCurrentPageImgEl.parentElement.dataset.scrollBackgroundRatio = "0";
                    onCurrentPageImgEl.remove();
                } else {
                    // Not an img nor a parallax: a regular background-image.
                    onCurrentPageImgEl.style.backgroundImage = "";
                    onCurrentPageImgEl.classList.remove(
                        "o_modified_image_to_save", "oe_img_bg", "o_bg_img_center"
                    );
                    attrsToRemove.forEach(attr => delete onCurrentPageImgEl.dataset[attr]);
                    $(onCurrentPageImgEl).trigger("background_changed", false);
                }
            }
        });
    },
});
});
