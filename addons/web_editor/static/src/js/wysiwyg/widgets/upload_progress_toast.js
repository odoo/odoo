/** @odoo-module */
import Widget from "web.Widget";
import {qweb} from 'web.core';

export const UploadProgressToast = Widget.extend({
    xmlDependencies: ['/web_editor/static/src/xml/wysiwyg.xml'],
    template: 'wysiwyg.widgets.upload.progress_toast',
    events: {
        'click .o_notification_close': '_onCloseClick',
    },

    /**
     * @override
     */
    init(parent, files) {
        this._super(...arguments);
        this.files = files;
    },
    /**
     * @override
     */
    start() {
        this.$progress = $('<div/>');
        _.each(this.files, (file, index) => {
            let fileSize = file.size;
            if (!fileSize) {
                fileSize = null;
            } else if (fileSize < 1024) {
                fileSize = fileSize.toFixed(2) + " bytes";
            } else if (fileSize < 1048576) {
                fileSize = (fileSize / 1024).toFixed(2) + " KB";
            } else {
                fileSize = (fileSize / 1048576).toFixed(2) + " MB";
            }

            this.$progress.append(qweb.render('wysiwyg.widgets.upload.progressbar', {
                fileId: index,
                fileName: file.name,
                fileSize: fileSize,
            }));
        });
        this.$el.find('.o_notification_content').append(this.$progress);
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
            this.el.querySelector('.fade').classList.remove('show');
            window.setTimeout(() => {
                this.destroy();
            }, 150);
        }, delay);
    },
    /**
     * Calls a RPC and shows its progress status.
     *
     * @param {Object} params regular `_rpc()` parameters
     * @param {integer} index file index to retrieve its related progress bar
     * @returns {Promise}
     */
    async rpcShowProgress(params, index) {
        let $progressBar = this.$el.find(`.js_progressbar_${index}`);
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
            const attachment = await this._rpc(params, {xhr});
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
