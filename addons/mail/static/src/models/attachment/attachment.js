/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2many, many2one, one2many } from '@mail/model/model_field';
import { clear, insert } from '@mail/model/model_field_command';

function factory(dependencies) {

    class Attachment extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            // Bind necessary until OWL supports arrow function in handlers: https://github.com/odoo/owl/issues/876
            this.onClickDownload = this.onClickDownload.bind(this);
        }


        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @static
         * @param {Object} data
         * @return {Object}
         */
        static convertData(data) {
            const data2 = {};
            if ('checksum' in data) {
                data2.checksum = data.checksum;
            }
            if ('filename' in data) {
                data2.filename = data.filename;
            }
            if ('id' in data) {
                data2.id = data.id;
            }
            if ('is_main' in data) {
                data2.is_main = data.is_main;
            }
            if ('mimetype' in data) {
                data2.mimetype = data.mimetype;
            }
            if ('name' in data) {
                data2.name = data.name;
            }
            // relation
            if ('res_id' in data && 'res_model' in data) {
                data2.originThread = insert({
                    id: data.res_id,
                    model: data.res_model,
                });
            }
            if ('originThread' in data) {
                data2.originThread = data.originThread;
            }
            return data2;
        }

        /**
         * Send the attachment for the browser to download.
         */
        download() {
            const downloadLink = document.createElement('a');
            downloadLink.setAttribute('href', this.downloadUrl);
            // Adding 'download' attribute into a link prevents open a new tab or change the current location of the window.
            // This avoids interrupting the activity in the page such as rtc call.
            downloadLink.setAttribute('download','');
            downloadLink.click();
        }

        /**
         * Handles click on download icon.
         *
         * @param {MouseEvent} ev
         */
        onClickDownload(ev) {
            ev.stopPropagation();
            this.download();
        }

        /**
         * Remove this attachment globally.
         */
        async remove() {
            if (this.isUnlinkPending) {
                return;
            }
            if (!this.isUploading) {
                this.update({ isUnlinkPending: true });
                try {
                    await this.env.services.rpc({
                        route: `/mail/attachment/delete`,
                        params: {
                            access_token: this.accessToken,
                            attachment_id: this.id,
                        },
                    }, { shadow: true });
                } finally {
                    if (this.exists()) {
                        this.update({ isUnlinkPending: false });
                    }
                }
            } else if (this.uploadingAbortController) {
                this.uploadingAbortController.abort();
            }
            if (this.exists()) {
                this.delete();
            }
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeDefaultSource() {
            if (this.isImage) {
                return `/web/image/${this.id}?signature=${this.checksum}`;
            }
            if (this.isPdf) {
                const pdf_lib = `/web/static/lib/pdfjs/web/viewer.html?file=`
                if (!this.accessToken && this.originThread && this.originThread.model === 'mail.channel') {
                    return `${pdf_lib}/mail/channel/${this.originThread.id}/attachment/${this.id}`;
                }
                const accessToken = this.accessToken ? `?access_token%3D${this.accessToken}` : '';
                return `${pdf_lib}/web/content/${this.id}${accessToken}`;
            }
            if (this.isUrlYoutube) {
                const urlArr = this.url.split('/');
                let token = urlArr[urlArr.length - 1];
                if (token.includes('watch')) {
                    token = token.split('v=')[1];
                    const amp = token.indexOf('&');
                    if (amp !== -1) {
                        token = token.substring(0, amp);
                    }
                }
                return `https://www.youtube.com/embed/${token}`;
            }
            if (!this.accessToken && this.originThread && this.originThread.model === 'mail.channel') {
                return `/mail/channel/${this.originThread.id}/attachment/${this.id}`;
            }
            const accessToken = this.accessToken ? `?access_token=${this.accessToken}` : '';
            return `/web/content/${this.id}${accessToken}`;
        }

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeDisplayName() {
            const displayName = this.name || this.filename;
            if (displayName) {
                return displayName;
            }
            return clear();
        }

        /**
         * @private
         * @returns {string}
         */
        _computeDownloadUrl() {
            if (!this.accessToken && this.originThread && this.originThread.model === 'mail.channel') {
                return `/mail/channel/${this.originThread.id}/attachment/${this.id}?download=true`;
            }
            const accessToken = this.accessToken ? `access_token=${this.accessToken}&` : '';
            return `/web/content/ir.attachment/${this.id}/datas?${accessToken}download=true`;
        }

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeExtension() {
            const extension = this.filename && this.filename.split('.').pop();
            if (extension) {
                return extension;
            }
            return clear();
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsEditable() {
            if (!this.messaging) {
                return;
            }

            if (this.messages.length && this.originThread && this.originThread.model === 'mail.channel') {
                return this.messages.some(message => (
                    message.canBeDeleted ||
                    (message.author && message.author === this.messaging.currentPartner) ||
                    (message.guestAuthor && message.guestAuthor === this.messaging.currentGuest)
                ));
            }
            return true;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsPdf() {
            return this.mimetype === 'application/pdf';
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsImage() {
            const imageMimetypes = [
                'image/bmp',
                'image/gif',
                'image/jpeg',
                'image/png',
                'image/svg+xml',
                'image/tiff',
                'image/x-icon',
            ];
            return imageMimetypes.includes(this.mimetype);
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsText() {
            const textMimeType = [
                'application/javascript',
                'application/json',
                'text/css',
                'text/html',
                'text/plain',
            ];
            return textMimeType.includes(this.mimetype);
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsVideo() {
            const videoMimeTypes = [
                'audio/mpeg',
                'video/x-matroska',
                'video/mp4',
                'video/webm',
            ];
            return videoMimeTypes.includes(this.mimetype);
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsUrl() {
            return this.type === 'url' && this.url;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsViewable() {
            return this.isText || this.isImage || this.isVideo || this.isPdf || this.isUrlYoutube;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsUrlYoutube() {
            return !!this.url && this.url.includes('youtu');
        }

        /**
         * @deprecated
         * @private
         * @returns {string}
         */
        _computeMediaType() {
            return this.mimetype && this.mimetype.split('/').shift();
        }

        /**
         * @private
         * @returns {AbortController|undefined}
         */
        _computeUploadingAbortController() {
            if (this.isUploading) {
                if (!this.uploadingAbortController) {
                    const abortController = new AbortController();
                    abortController.signal.onabort = () => {
                        this.messaging.messagingBus.trigger('o-attachment-upload-abort', {
                            attachment: this
                        });
                    };
                    return abortController;
                }
                return this.uploadingAbortController;
            }
            return;
        }
    }

    Attachment.fields = {
        accessToken: attr(),
        activities: many2many('mail.activity', {
            inverse: 'attachments',
        }),
        /**
         * States the attachment cards that are displaying this attachment.
         */
        attachmentCards: one2many('mail.attachment_card', {
            inverse: 'attachment',
            isCausal: true,
        }),
        /**
         * States the attachment images that are displaying this attachment.
         */
        attachmentImages: one2many('mail.attachment_image', {
            inverse: 'attachment',
            isCausal: true,
        }),
        /**
         * States the attachment lists that are displaying this attachment.
         */
        attachmentLists: many2many('mail.attachment_list', {
            inverse: 'attachments',
        }),
        attachmentViewer: many2many('mail.attachment_viewer', {
            inverse: 'attachments',
        }),
        checksum: attr(),
        /**
         * States on which composer this attachment is currently being created.
         */
        composer: many2one('mail.composer', {
            inverse: 'attachments',
        }),
        defaultSource: attr({
            compute: '_computeDefaultSource',
        }),
        /**
         * States the OWL ref of the "dialog" window.
         */
        dialogRef: attr(),
        displayName: attr({
            compute: '_computeDisplayName',
        }),
        downloadUrl: attr({
           compute: '_computeDownloadUrl',
        }),
        extension: attr({
            compute: '_computeExtension',
        }),
        filename: attr(),
        id: attr({
            readonly: true,
            required: true,
        }),
        /**
         * States whether this attachment is editable.
         */
        isEditable: attr({
            compute: '_computeIsEditable',
        }),
        /**
         * States id the attachment is an image.
         */
        isImage: attr({
            compute: '_computeIsImage',
        }),
        is_main: attr(),
        /**
         * States if the attachment is a PDF file.
         */
        isPdf: attr({
            compute: '_computeIsPdf',
        }),
        /**
         * States if the attachment is a text file.
         */
        isText: attr({
            compute: '_computeIsText',
        }),
        /**
         * True if an unlink RPC is pending, used to prevent multiple unlink attempts.
         */
        isUnlinkPending: attr({
            default: false,
        }),
        isUploading: attr({
            default: false,
        }),
        /**
         * States if the attachment is an url.
         */
        isUrl: attr({
            compute: '_computeIsUrl',
        }),
        /**
         * Determines if the attachment is a youtube url.
         */
        isUrlYoutube: attr({
            compute: '_computeIsUrlYoutube',
        }),
        /**
         * States if the attachment is a video.
         */
        isVideo: attr({
            compute: '_computeIsVideo',
        }),
        isViewable: attr({
            compute: '_computeIsViewable',
        }),
        /**
         * @deprecated
         */
        mediaType: attr({
            compute: '_computeMediaType',
        }),
        messages: many2many('mail.message', {
            inverse: 'attachments',
        }),
        mimetype: attr({
            default: '',
        }),
        name: attr(),
        originThread: many2one('mail.thread', {
            inverse: 'originThreadAttachments',
        }),
        size: attr(),
        threads: many2many('mail.thread', {
            inverse: 'attachments',
        }),
        type: attr(),
        /**
         * Abort Controller linked to the uploading process of this attachment.
         * Useful in order to cancel the in-progress uploading of this attachment.
         */
        uploadingAbortController: attr({
            compute: '_computeUploadingAbortController',
        }),
        url: attr(),
    };
    Attachment.identifyingFields = ['id'];
    Attachment.modelName = 'mail.attachment';

    return Attachment;
}

registerNewModel('mail.attachment', factory);
