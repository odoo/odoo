odoo.define('web_editor.ImageManager', function (require) {
'use strict';

const core = require('web.core');
const _t = core._t;
const RESIZE_TYPES = ['image/jpeg', 'image/jpe', 'image/jpg', 'image/png'];
const QUALITY_TYPES = ['image/jpeg', 'image/jpe', 'image/jpg', 'image/png'];
/**
 * Manages an image optimization (quality and resizing).
 */
const ImageManager = core.Class.extend({
    /**
     * Constructor
     */
    init: function (img, rpc) {
        this.img = img;
        this.rpc = rpc;
        this.width = img.naturalWidth;
        this.optimizeOnSave = false;
        this.callbacks = [];
        $(this.img).on('image_changed.ImageManager', this.onImageChanged.bind(this));
        // Memoizing to prevent getting a network call on every UI update.
        this.getImageWeight = _.memoize(this.getImageWeight.bind(this), () => this.img.src);
    },
    destroy: function () {
        $(this.img).off('.ImageManager');
    },
    /**
     * Changes the image's quality.
     */
    changeImageQuality: function (quality) {
        this.quality = quality;
        this.optimizeOnSave = true;
        this.updatePreview();
    },
    /**
     * Finds the db attachment that corresponds the the image's src attribute.
     */
    loadAttachment: async function () {
        // If there was already an initial attachment but we're loading a new one,
        // the original has been replaced, the old one should be marked for deletion.
        if (this.initialAttachment && this.initialAttachment.original_id) {
            this.img.dataset.unlinkAttachment = this.initialAttachment.id;
        }
        this.originalSrc = this.img.getAttribute('src') || "";
        const url = this.originalSrc.split(/[?#]/)[0];
        if (!url) {
            return await this.updateAttachment([]);
        }
        const attachments = await this.rpc({
            model: 'ir.attachment',
            method: 'search_read',
            args: [],
            kwargs: {
                domain: [['image_src', '=like', url]],
                fields: ['type', 'original_id', 'quality', 'name', 'image_src', 'mimetype'],
            },
        });
        return await this.updateAttachment(attachments);
    },
    /**
     * Updates the internal state to that of the attachment, if it's not an
     * original, queries the database for the original to get its id.
     */
    updateAttachment: async function (attachments) {
        if (attachments.length && !this.initialAttachment) {
            this.initialAttachment = attachments[0];
        }
        this.width = Math.min(this.computeOptimizedWidth(), this.img.naturalWidth);
        this.attachment = attachments[0];
        if (this.attachment && this.attachment.type === "binary") {
            let record;
            if (this.attachment.original_id) {
                [record] = await this.rpc({
                    model: 'ir.attachment',
                    method: 'read',
                    args: [this.attachment.original_id[0]],
                });
            }
            this.originalId = this.attachment.original_id[0] || this.attachment.id;
            this.quality = this.attachment.original_id ? this.attachment.quality : 80;
            this.updatePreview();
            const original = record || this.attachment;
            const $img = $('<img>', {src: `/web/image/${original.id}`});
            const originalImg = await new Promise(resolve => $img.one('load', ev => resolve($img[0])));
            this.originalWidth = originalImg.naturalWidth;
        } else {
            delete this.attachment;
        }
        await Promise.all(this.callbacks.map(cb => cb()));
    },
    /**
     * Returns the weight of the image in bytes.
     */
    getImageWeight: async function () {
        if (this.img.getAttribute('src')) {
            const resp = await window.fetch(this.img.src, {method: 'HEAD'});
            return resp.headers.get('Content-Length');
        }
        return 0;
    },
    /**
     * Changes the image's width.
     */
    changeImageWidth: function (width) {
        this.width = width;
        this.optimizeOnSave = true;
        this.updatePreview();
    },
    /**
     * Updates the image preview.
     */
    updatePreview: function () {
        if (this.attachment) {
            this.img.src = `/web/image/${this.originalId}/?width=${this.width}&quality=${this.quality}`;
        }
    },
    /**
     * Computes the image's maximum display width.
     */
    computeOptimizedWidth: function () {
        const displayWidth = this.img.clientWidth || this.img.naturalWidth;
        const $img = $(this.img);
        // If the image is in a column, it might get bigger on smaller screens.
        // We use col-lg for this in most (all?) snippets.
        if ($img.closest('[class*="col-lg"]').length) {
            // A container's maximum inner width is 690px on the md breakpoint
            if ($img.closest('.container').length) {
                return Math.min(1920, Math.max(displayWidth, 690));
            }
            // A container-fluid's max inner width is 962px on the md breakpoint
            return Math.min(1920, Math.max(displayWidth, 962));
        }
        // If it's not in a col-lg, it's *probably* not going to change size depending on breakpoints
        return displayWidth;
    },
    /**
     * Returns an object containing the available widths for the image, where
     * the keys are the widths themselves, and values are an array of labels.
     */
    computeAvailableWidths: function () {
        const widths = [
            [128, []],
            [256, []],
            [512, []],
            [1024, []],
            [1920, []],
            [this.computeOptimizedWidth(), [_t("recommended")]],
            [this.originalWidth, [_t("original")]],
        ];
        this.availableWidths = widths.filter(w => w[0] <= this.originalWidth)
            .sort((a, b) => a[0] - b[0])
            .reduce((acc, v) => {
            acc[v[0]] = (acc[v[0]] || []).concat(v[1]);
            return acc;
        }, {});
        return this.availableWidths;
    },
    /**
     * Saves an optimized copy of the original image, sets the <img/> element's
     * src to the public url of the copy.
     */
    cleanForSave: async function () {
        if (this.isClean) {
            return;
        }
        this.isClean = true;
        if (this.optimizeOnSave) {
            if (this.initialAttachment && this.initialAttachment.original_id) {
                this.img.dataset.unlinkAttachment = this.initialAttachment.id;
            }
            if (this.attachment) {
                const optimizedImage = await this.rpc({
                    route: `/web_editor/attachment/${this.originalId}/update`,
                    params: {
                        copy: true,
                        quality: this.quality,
                        width: this.width,
                    },
                });
                this.img.src = optimizedImage.image_src;
            }
        } else {
            this.img.src = this.originalSrc;
        }
    },
    /**
     * Allows options to execute code when the attachment changes.
     */
    onUpdateAttachment: function (cb) {
        this.callbacks.push(cb);
    },
    /**
     * Updates the state if the image is changed by the user.
     *
     * @private
     */
    onImageChanged: async function (ev) {
        await this.loadAttachment();
        this.optimizeOnSave = true;
    },
    /**
     * @returns {quality: Boolean} whether the image's quality can be changed
     * @returns {size: Boolean} whether the image can be resized
     */
    getOptions: function () {
        if (!this.attachment) {
            return {quality: false, size: false};
        }
        return {
            quality: QUALITY_TYPES.includes(this.attachment.mimetype),
            size: RESIZE_TYPES.includes(this.attachment.mimetype),
        };
    },
});

return ImageManager;
});
