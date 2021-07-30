/** @odoo-module */

import Widget from "web.Widget";
import concurrency from "web.concurrency";
import { getDataURLFromFile } from "web.utils";

export const UploadProgressToast = Widget.extend({
    xmlDependencies: ['/web_editor/static/src/xml/wysiwyg.xml'],
    template: 'wysiwyg.widgets.upload.progress_toast',
    events: {
        'click .o_notification_close': '_onCloseClick',
    },

    /**
     * @override
     */
    init(parent, { files, resModel, resId, isImage }) {
        this._super(...arguments);
        this.resId = resId;
        this.resModel = resModel;
        this.isImage = isImage;

        // Upload the smallest file first to block the user the least possible.
        this.files = [...files].sort((a, b) => a.size - b.size);
        this.files.forEach((file, index) => {
            file.id = index;
            if (!file.size) {
                file.displaySize = null;
            } else if (file.size < 1024) {
                file.displaySize = file.size.toFixed(2) + " bytes";
            } else if (file.size < 1048576) {
                file.displaySize = (file.size / 1024).toFixed(2) + " KB";
            } else {
                file.displaySize = (file.size / 1048576).toFixed(2) + " MB";
            }
        });
    },
    /**
     * @override
     */
    start() {
        this.hasError = false;
        const uploadMutex = new concurrency.Mutex();
        this.files.forEach((file, index) => {
            // Upload one file at a time: no need to parallel as upload is
            // limited by bandwidth.
            uploadMutex.exec(async () => {
                const dataURL = await getDataURLFromFile(file);
                const attachment = await this._rpcShowProgress({
                    route: '/web_editor/attachment/add_data',
                    params: {
                        name: file.name,
                        data: dataURL.split(',')[1],
                        res_id: this.resId,
                        res_model: this.resModel,
                        is_image: this.isImage,
                        width: 0,
                        quality: 0,
                    }
                }, this.$el.find(`.js_progressbar_${index}`));
                if (!attachment.error) {
                    this.trigger_up('file_complete', attachment);
                }
            });
        });

        uploadMutex.getUnlockedDef().then(() => {
            this.trigger_up('upload_complete');
            this.destroyOnClose = true;
            this.close(2000);
        });
        this.uploadMutex = uploadMutex;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Calls a RPC and shows its progress status.
     *
     * @public
     * @param {Number} delay time to wait before closing the toast
     */
     close(delay = 0) {
        window.setTimeout(() => {
            if (!this.hasError || delay === 0) {
                this.el.querySelector('.fade').classList.remove('show');
                window.setTimeout(() => {
                    if (this.destroyOnClose) {
                        this.destroy();
                    } else {
                        this.el.classList.add('d-none');
                    }
                }, 150);
            }
        }, delay);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Calls a RPC and shows its progress status.
     *
     * @private
     * @param {Object} params regular `_rpc()` parameters
     * @param {jQuery} $progressBar the element holding the progress bar
     * @returns {Promise} resolved when the RPC is complete
     */
    async _rpcShowProgress(params, $progressBar) {
        try {
            const xhr = new XMLHttpRequest();
            xhr.upload.addEventListener('progress', ev => {
                const prcComplete = ev.loaded / ev.total * 100;
                $progressBar.find('.progress-bar').css({
                    width: Math.floor(prcComplete) + '%',
                }).text(prcComplete.toFixed(2) + '%');
            });
            xhr.upload.addEventListener('load', function () {
                // Don't show yet success as backend code only starts now
                $progressBar.find('.progress-bar').css({width: '100%'}).text('100%');
            });
            const attachment = await this._rpc(params, { xhr });
            $progressBar.find('.fa-spinner, .progress').addClass('d-none');
            if (attachment.error) {
                this.hasError = true;
                $progressBar.find('.js_progressbar_txt .text-danger').removeClass('d-none');
                $progressBar.find('.js_progressbar_txt .text-danger .o_we_error_text').text(attachment.error);
            } else {
                $progressBar.find('.js_progressbar_txt .text-success').removeClass('d-none');
            }
            return attachment;
        } catch (error) {
            this.hasError = true;
            $progressBar.find('.fa-spinner, .progress').addClass('d-none');
            $progressBar.find('.js_progressbar_txt .text-danger').removeClass('d-none');
            throw error;
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onCloseClick() {
        this.close();
    },
});
