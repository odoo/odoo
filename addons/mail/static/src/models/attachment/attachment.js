odoo.define('mail/static/src/models/attachment/attachment.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2many, many2one } = require('mail/static/src/model/model_field.js');
const { clear } = require('mail/static/src/model/model_field_command.js');

function factory(dependencies) {

    let nextTemporaryId = -1;
    function getAttachmentNextTemporaryId() {
        const id = nextTemporaryId;
        nextTemporaryId -= 1;
        return id;
    }
    class Attachment extends dependencies['mail.model'] {

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
            if ('filename' in data) {
                data2.filename = data.filename;
            }
            if ('id' in data) {
                data2.id = data.id;
            }
            if ('mimetype' in data) {
                data2.mimetype = data.mimetype;
            }
            if ('name' in data) {
                data2.name = data.name;
            }

            // relation
            if ('res_id' in data && 'res_model' in data) {
                data2.originThread = [['insert', {
                    id: data.res_id,
                    model: data.res_model,
                }]];
            }

            return data2;
        }

        /**
         * @override
         */
        static create(data) {
            const isMulti = typeof data[Symbol.iterator] === 'function';
            const dataList = isMulti ? data : [data];
            for (const data of dataList) {
                if (!data.id) {
                    data.id = getAttachmentNextTemporaryId();
                }
            }
            return super.create(...arguments);
        }

        /**
         * View provided attachment(s), with given attachment initially. Prompts
         * the attachment viewer.
         *
         * @static
         * @param {Object} param0
         * @param {mail.attachment} [param0.attachment]
         * @param {mail.attachments[]} param0.attachments
         * @returns {string|undefined} unique id of open dialog, if open
         */
        static view({ attachment, attachments }) {
            const hasOtherAttachments = attachments && attachments.length > 0;
            if (!attachment && !hasOtherAttachments) {
                return;
            }
            if (!attachment && hasOtherAttachments) {
                attachment = attachments[0];
            } else if (attachment && !hasOtherAttachments) {
                attachments = [attachment];
            }
            if (!attachments.includes(attachment)) {
                return;
            }
            this.env.messaging.dialogManager.open('mail.attachment_viewer', {
                attachment: [['link', attachment]],
                attachments: [['replace', attachments]],
            });
        }

        /**
         * Remove this attachment globally.
         */
        async remove() {
            if (this.isUnlinkPending) {
                return;
            }
            if (!this.isTemporary) {
                this.update({ isUnlinkPending: true });
                try {
                    await this.async(() => this.env.services.rpc({
                        model: 'ir.attachment',
                        method: 'unlink',
                        args: [this.id],
                    }, { shadow: true }));
                } finally {
                    this.update({ isUnlinkPending: false });
                }
            } else if (this.uploadingAbortController) {
                this.uploadingAbortController.abort();
            }
            this.delete();
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return `${this.modelName}_${data.id}`;
        }

        /**
         * @private
         * @returns {mail.composer[]}
         */
        _computeComposers() {
            if (this.isTemporary) {
                return [];
            }
            const relatedTemporaryAttachment = this.env.models['mail.attachment']
                .find(attachment =>
                    attachment.filename === this.filename &&
                    attachment.isTemporary
                );
            if (relatedTemporaryAttachment) {
                const composers = relatedTemporaryAttachment.composers;
                relatedTemporaryAttachment.delete();
                return [['replace', composers]];
            }
            return [];
        }

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeDefaultSource() {
            if (this.fileType === 'image') {
                return `/web/image/${this.id}?unique=1&amp;signature=${this.checksum}&amp;model=ir.attachment`;
            }
            if (this.fileType === 'application/pdf') {
                return `/web/static/lib/pdfjs/web/viewer.html?file=/web/content/${this.id}?model%3Dir.attachment`;
            }
            if (this.fileType && this.fileType.includes('text')) {
                return `/web/content/${this.id}?model%3Dir.attachment`;
            }
            if (this.fileType === 'youtu') {
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
            if (this.fileType === 'video') {
                return `/web/image/${this.id}?model=ir.attachment`;
            }
            return clear();
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
         * @returns {string|undefined}
         */
        _computeFileType() {
            if (this.type === 'url' && !this.url) {
                return clear();
            } else if (!this.mimetype) {
                return clear();
            }
            const match = this.type === 'url'
                ? this.url.match('(youtu|.png|.jpg|.gif)')
                : this.mimetype.match('(image|video|application/pdf|text)');
            if (!match) {
                return clear();
            }
            if (match[1].match('(.png|.jpg|.gif)')) {
                return 'image';
            }
            return match[1];
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsLinkedToComposer() {
            return this.composers.length > 0;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsTextFile() {
            if (!this.fileType) {
                return false;
            }
            return this.fileType.includes('text');
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsViewable() {
            return (
                this.mediaType === 'image' ||
                this.mediaType === 'video' ||
                this.mimetype === 'application/pdf' ||
                this.isTextFile
            );
        }

        /**
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
            if (this.isTemporary) {
                if (!this.uploadingAbortController) {
                    const abortController = new AbortController();
                    abortController.signal.onabort = () => {
                        this.env.messagingBus.trigger('o-attachment-upload-abort', {
                            attachment: this
                        });
                    };
                    return abortController;
                }
                return this.uploadingAbortController;
            }
            return undefined;
        }
    }

    Attachment.fields = {
        activities: many2many('mail.activity', {
            inverse: 'attachments',
        }),
        attachmentViewer: many2many('mail.attachment_viewer', {
            inverse: 'attachments',
        }),
        checkSum: attr(),
        composers: many2many('mail.composer', {
            compute: '_computeComposers',
            inverse: 'attachments',
        }),
        defaultSource: attr({
            compute: '_computeDefaultSource',
            dependencies: [
                'checkSum',
                'fileType',
                'id',
                'url',
            ],
        }),
        displayName: attr({
            compute: '_computeDisplayName',
            dependencies: [
                'filename',
                'name',
            ],
        }),
        extension: attr({
            compute: '_computeExtension',
            dependencies: ['filename'],
        }),
        filename: attr(),
        fileType: attr({
            compute: '_computeFileType',
            dependencies: [
                'mimetype',
                'type',
                'url',
            ],
        }),
        id: attr(),
        isLinkedToComposer: attr({
            compute: '_computeIsLinkedToComposer',
            dependencies: ['composers'],
        }),
        isTemporary: attr({
            default: false,
        }),
        isTextFile: attr({
            compute: '_computeIsTextFile',
            dependencies: ['fileType'],
        }),
        /**
         * True if an unlink RPC is pending, used to prevent multiple unlink attempts.
         */
        isUnlinkPending: attr({
            default: false,
        }),
        isViewable: attr({
            compute: '_computeIsViewable',
            dependencies: [
                'mediaType',
                'isTextFile',
                'mimetype',
            ],
        }),
        mediaType: attr({
            compute: '_computeMediaType',
            dependencies: ['mimetype'],
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
            dependencies: [
                'isTemporary',
                'uploadingAbortController',
            ],
        }),
        url: attr(),
    };

    Attachment.modelName = 'mail.attachment';

    return Attachment;
}

registerNewModel('mail.attachment', factory);

});
