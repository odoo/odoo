odoo.define('web.fileUploadMixin', function (require) {
'use strict';

/**
 * Mixin to be used in view Controllers to manage uploads and generate progress bars.
 * supported views: kanban, list
 */

const { csrf_token, _t } = require('web.core');
const ProgressBar = require('web.ProgressBar');
const ProgressCard = require('web.ProgressCard');

const ProgressBarMixin = {

    custom_events: {
        progress_bar_abort: '_onProgressBarAbort',
    },

    init() {
        /**
         * Contains the uploads currently happening, used to attach progress bars.
         * e.g: {'fileUploadId45': {progressBar, progressCard, ...params}}
         */
        this._fileUploads = {};
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * used to use a mocked version of Xhr in the tests.
     *
     * @private
     * @returns {XMLHttpRequest}
     */
    _createXhr() {
        return new window.XMLHttpRequest();
    },
    /**
     * @private
     */
    _getFileUploadRenderOptions() {
        return {
            predicate: () => true,
            targetCallback: undefined,
        };
    },
    /**
     * @private
     * @returns {string} upload route
     */
    _getFileUploadRoute() {
        return '/web/binary/upload_attachment';
    },
    /**
     * @private
     * @param {Object} params
     * @param {Object[]} params.files
     * @param {XMLHttpRequest} params.xhr
     */
    _makeFileUpload(params) {
        const { files, xhr } = params;
        const fileUploadId = _.uniqueId('fileUploadId');
        const formData = new FormData();
        const formDataKeys = this._makeFileUploadFormDataKeys(Object.assign({ fileUploadId }, params));

        formData.append('csrf_token', csrf_token);
        for (const key in formDataKeys) {
            if (formDataKeys[key] !== undefined) {
                formData.append(key, formDataKeys[key]);
            }
        }
        for (const file of files) {
            formData.append('ufile', file);
        }

        return {
            fileUploadId,
            xhr,
            title: files.length === 1
                ? files[0].name
                : _.str.sprintf(_t("%s Files"), files.length),
            type: files.length === 1 ? files[0].type : undefined,
            formData,
        };
    },
    /**
     * @private
     * @param {Object} param0
     * @param {string} param0.fileUploadId
     * @returns {Object} the list of the form entries of a file upload.
     */
    _makeFileUploadFormDataKeys({ fileUploadId }) {
        return {
            callback: fileUploadId,
        };
    },
    /**
     * @private
     * @param {integer} fileUploadId
     */
    async _removeFileUpload(fileUploadId) {
        const upload = this._fileUploads[fileUploadId];
        upload.progressCard && upload.progressCard.destroy();
        upload.progressBar && upload.progressBar.destroy();
        delete this._fileUploads[fileUploadId];
        await this.reload();
    },
    /**
     * @private
     */
    async _renderFileUploads() {
        const { predicate, targetCallback } = this._getFileUploadRenderOptions();

        for (const fileUploadId in this._fileUploads) {
            const upload = this._fileUploads[fileUploadId];
            if (!predicate(upload)) {
                continue;
            }

            if (!upload.progressBar) {
                if (!upload.recordId || this.viewType !== 'kanban') {
                    upload.progressCard = new ProgressCard(this, {
                        title: upload.title,
                        type: upload.type,
                        viewType: this.viewType,
                    });
                }
                upload.progressBar = new ProgressBar(this, {
                    xhr: upload.xhr,
                    title: upload.title,
                    fileUploadId,
                });
            }

            let $targetCard;
            if (upload.progressCard) {
                await upload.progressCard.prependTo(this.renderer.$el);
                $targetCard = upload.progressCard.$el;
            } else if (targetCallback) {
                $targetCard = targetCallback(upload);
            }
            await upload.progressBar.appendTo($targetCard);
        }
    },
    /**
     * @private
     * @param {Object[]} files
     * @param {Object} [params] optional additional data
     */
    async _uploadFiles(files, params={}) {
        if (!files || !files.length) { return; }

        await new Promise(resolve => {
            const xhr = this._createXhr();
            xhr.open('POST', this._getFileUploadRoute());
            const fileUploadData = this._makeFileUpload(Object.assign({ files, xhr }, params));
            const { fileUploadId, formData } = fileUploadData;
            this._fileUploads[fileUploadId] = fileUploadData;
            xhr.upload.addEventListener("progress", ev => {
                this._updateFileUploadProgress(fileUploadId, ev);
            });
            const progressPromise = this._onBeforeUpload();
            xhr.onload = async () => {
                await progressPromise;
                resolve();
                this._onUploadLoad({ fileUploadId, xhr });
            };
            xhr.onerror = async () => {
                await progressPromise;
                resolve();
                this._onUploadError({ fileUploadId, xhr });
            };
            xhr.send(formData);
        });
    },
    /**
     * @private
     * @param {string} fileUploadId
     * @param {ProgressEvent} ev
     */
    _updateFileUploadProgress(fileUploadId, ev) {
        const { progressCard, progressBar } = this._fileUploads[fileUploadId];
        progressCard && progressCard.update(ev.loaded, ev.total);
        progressBar && progressBar.update(ev.loaded, ev.total);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Hook to customize the behaviour of _uploadFiles() before an upload is made.
     *
     * @private
     */
    async _onBeforeUpload() {
        await this._renderFileUploads();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {integer} ev.data.fileUploadId
     */
    _onProgressBarAbort(ev) {
        this._removeFileUpload(ev.data.fileUploadId);
    },
    /**
     * Hook to customize the behaviour of the xhr.onload of an upload.
     *
     * @private
     * @param {string} param0.fileUploadId
     */
    _onUploadLoad({ fileUploadId }) {
        this._removeFileUpload(fileUploadId);
    },
    /**
     * Hook to customize the behaviour of the xhr.onerror of an upload.
     *
     * @private
     * @param {string} param1.fileUploadId
     * @param {XMLHttpRequest} param0.xhr
     */
    _onUploadError({ fileUploadId, xhr }) {
        this.do_notify(xhr.status, _.str.sprintf(_t('message: %s'), xhr.reponseText), true);
        this._removeFileUpload(fileUploadId);
    },

};

return ProgressBarMixin;

});
