odoo.define('mail/static/src/models/attachment/attachment.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { clear } = require('mail/static/src/model/model_field_command.js');
const { attr, many2many, many2one } = require('mail/static/src/model/model_field_utils.js');

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
                data2.__mfield_filename = data.filename;
            }
            if ('id' in data) {
                data2.__mfield_id = data.id;
            }
            if ('mimetype' in data) {
                data2.__mfield_mimetype = data.mimetype;
            }
            if ('name' in data) {
                data2.__mfield_name = data.name;
            }

            // relation
            if ('res_id' in data && 'res_model' in data) {
                data2.__mfield_originThread = [['insert', {
                    __mfield_id: data.res_id,
                    __mfield_model: data.res_model,
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
                if (!data.__mfield_id) {
                    data.__mfield_id = getAttachmentNextTemporaryId();
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
            this.env.messaging.__mfield_dialogManager(this).open('mail.attachment_viewer', {
                __mfield_attachment: [['link', attachment]],
                __mfield_attachments: [['replace', attachments]],
            });
        }

        /**
         * Remove this attachment globally.
         */
        async remove() {
            if (!this.__mfield_isTemporary(this)) {
                await this.async(() => this.env.services.rpc({
                    model: 'ir.attachment',
                    method: 'unlink',
                    args: [this.__mfield_id(this)],
                }, { shadow: true }));
            } else if (this.__mfield_uploadingAbortController(this)) {
                this.__mfield_uploadingAbortController(this).abort();
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
            return `${this.modelName}_${data.__mfield_id}`;
        }

        /**
         * @private
         * @returns {mail.composer[]}
         */
        _computeComposers() {
            if (this.__mfield_isTemporary(this)) {
                return [];
            }
            const relatedTemporaryAttachment = this.env.models['mail.attachment']
                .find(attachment =>
                    attachment.__mfield_filename(this) === this.__mfield_filename(this) &&
                    attachment.__mfield_isTemporary(this)
                );
            if (relatedTemporaryAttachment) {
                const composers = relatedTemporaryAttachment.__mfield_composers(this);
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
            if (this.__mfield_fileType(this) === 'image') {
                return `/web/image/${this.__mfield_id(this)}?unique=1&amp;signature=${this.__mfield_checkSum(this)}&amp;model=ir.attachment`;
            }
            if (this.__mfield_fileType(this) === 'application/pdf') {
                return `/web/static/lib/pdfjs/web/viewer.html?file=/web/content/${this.__mfield_id(this)}?model%3Dir.attachment`;
            }
            if (this.__mfield_fileType(this) && this.__mfield_fileType(this).includes('text')) {
                return `/web/content/${this.__mfield_id(this)}?model%3Dir.attachment`;
            }
            if (this.__mfield_fileType(this) === 'youtu') {
                const urlArr = this.__mfield_url(this).split('/');
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
            if (this.__mfield_fileType(this) === 'video') {
                return `/web/image/${this.__mfield_id(this)}?model=ir.attachment`;
            }
            return clear();
        }

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeDisplayName() {
            const displayName = this.__mfield_name(this) || this.__mfield_filename(this);
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
            const extension = this.__mfield_filename(this) && this.__mfield_filename(this).split('.').pop();
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
            if (this.__mfield_type(this) === 'url' && !this.__mfield_url(this)) {
                return clear();
            } else if (!this.__mfield_mimetype(this)) {
                return clear();
            }
            const match = this.__mfield_type(this) === 'url'
                ? this.__mfield_url(this).match('(youtu|.png|.jpg|.gif)')
                : this.__mfield_mimetype(this).match('(image|video|application/pdf|text)');
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
            return this.__mfield_composers(this).length > 0;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsTextFile() {
            if (!this.__mfield_fileType(this)) {
                return false;
            }
            return this.__mfield_fileType(this).includes('text');
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsViewable() {
            return (
                this.__mfield_mediaType(this) === 'image' ||
                this.__mfield_mediaType(this) === 'video' ||
                this.__mfield_mimetype(this) === 'application/pdf' ||
                this.__mfield_isTextFile(this)
            );
        }

        /**
         * @private
         * @returns {string}
         */
        _computeMediaType() {
            return this.__mfield_mimetype(this) && this.__mfield_mimetype(this).split('/').shift();
        }

        /**
         * @private
         * @returns {AbortController|undefined}
         */
        _computeUploadingAbortController() {
            if (this.__mfield_isTemporary(this)) {
                if (!this.__mfield_uploadingAbortController(this)) {
                    const abortController = new AbortController();
                    abortController.signal.onabort = () => {
                        this.env.messagingBus.trigger('o-attachment-upload-abort', {
                            attachment: this
                        });
                    };
                    return abortController;
                }
                return this.__mfield_uploadingAbortController(this);
            }
            return undefined;
        }
    }

    Attachment.fields = {
        __mfield_activities: many2many('mail.activity', {
            inverse: '__mfield_attachments',
        }),
        __mfield_attachmentViewer: many2many('mail.attachment_viewer', {
            inverse: '__mfield_attachments',
        }),
        __mfield_checkSum: attr(),
        __mfield_composers: many2many('mail.composer', {
            compute: '_computeComposers',
            inverse: '__mfield_attachments',
        }),
        __mfield_defaultSource: attr({
            compute: '_computeDefaultSource',
            dependencies: [
                '__mfield_checkSum',
                '__mfield_fileType',
                '__mfield_id',
                '__mfield_url',
            ],
        }),
        __mfield_displayName: attr({
            compute: '_computeDisplayName',
            dependencies: [
                '__mfield_filename',
                '__mfield_name',
            ],
        }),
        __mfield_extension: attr({
            compute: '_computeExtension',
            dependencies: [
                '__mfield_filename',
            ],
        }),
        __mfield_filename: attr(),
        __mfield_fileType: attr({
            compute: '_computeFileType',
            dependencies: [
                '__mfield_mimetype',
                '__mfield_type',
                '__mfield_url',
            ],
        }),
        __mfield_id: attr(),
        __mfield_isLinkedToComposer: attr({
            compute: '_computeIsLinkedToComposer',
            dependencies: [
                '__mfield_composers',
            ],
        }),
        __mfield_isTemporary: attr({
            default: false,
        }),
        __mfield_isTextFile: attr({
            compute: '_computeIsTextFile',
            dependencies: [
                '__mfield_fileType',
            ],
        }),
        __mfield_isViewable: attr({
            compute: '_computeIsViewable',
            dependencies: [
                '__mfield_mediaType',
                '__mfield_isTextFile',
                '__mfield_mimetype',
            ],
        }),
        __mfield_mediaType: attr({
            compute: '_computeMediaType',
            dependencies: [
                '__mfield_mimetype',
            ],
        }),
        __mfield_messages: many2many('mail.message', {
            inverse: '__mfield_attachments',
        }),
        __mfield_mimetype: attr({
            default: '',
        }),
        __mfield_name: attr(),
        __mfield_originThread: many2one('mail.thread', {
            inverse: '__mfield_originThreadAttachments',
        }),
        __mfield_size: attr(),
        __mfield_threads: many2many('mail.thread', {
            inverse: '__mfield_attachments',
        }),
        /**
         * Abort Controller linked to the uploading process of this attachment.
         * Useful in order to cancel the in-progress uploading of this attachment.
         */
        __mfield_uploadingAbortController: attr({
            compute: '_computeUploadingAbortController',
            dependencies: [
                '__mfield_isTemporary',
                '__mfield_uploadingAbortController',
            ],
        }),
        __mfield_type: attr(),
        __mfield_url: attr(),
    };

    Attachment.modelName = 'mail.attachment';

    return Attachment;
}

registerNewModel('mail.attachment', factory);

});
