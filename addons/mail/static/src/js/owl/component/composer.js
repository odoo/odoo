odoo.define('mail.component.Composer', function (require) {
'use strict';

const AttachmentList = require('mail.component.AttachmentList');
const DropZone = require('mail.component.DropZone');
const EmojisButton = require('mail.component.EmojisButton');
const TextInput = require('mail.component.ComposerTextInput');

const core = require('web.core');

class Composer extends owl.Component {

    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.fileuploadId = _.uniqueId('o_Composer_fileupload');
        this.state = owl.useState({
            hasAllSuggestedRecipients: false,
            hasDropZone: false,
            hasTextInputContent: false,
        });
        this.storeDispatch = owl.hooks.useDispatch();
        this.storeGetters = owl.hooks.useGetters();
        this.storeProps = owl.hooks.useStore((state, props) => {
            const storeComposerState = _.defaults({}, state.composers[props.id], {
                attachmentLocalIds: [],
            });
            return Object.assign({}, storeComposerState, {
                fullSuggestedRecipients: (props.suggestedRecipients || []).map(recipient => {
                    return Object.assign({}, recipient, {
                        partner: state.partners[recipient.partnerLocalId],
                    });
                }),
                isMobile: state.isMobile,
                thread: state.threads[props.threadLocalId],
            });
        });
        this._emojisButtonRef = owl.hooks.useRef('emojisButton');
        this._fileInputRef = owl.hooks.useRef('fileInput');
        this._dropzoneRef = owl.hooks.useRef('dropzone');
        /**
         * Counts how many drag enter/leave happened globally. This is the only
         * way to know if a file has been dragged out of the browser window.
         */
        this._dragCount = 0;
        /**
         * Tracked focus counter from props. Useful to determine whether it
         * should auto focus this composer when patched.
         */
        this._focusCount = 0;
        this._onClickCaptureGlobal = this._onClickCaptureGlobal.bind(this);
        this._onDragenterCaptureGlobal = this._onDragenterCaptureGlobal.bind(this);
        this._onDragleaveCaptureGlobal = this._onDragleaveCaptureGlobal.bind(this);
        this._onDropCaptureGlobal = this._onDropCaptureGlobal.bind(this);
        this._textInputRef = owl.hooks.useRef('textInput');
    }

    mounted() {
        this._attachmentUploadedEventListener = (...args) => this._onAttachmentUploaded(...args);
        $(window).on(this.fileuploadId, this._attachmentUploadedEventListener);
        if (this.props.isFocusOnMount) {
            this.focus();
        }
        if (this.env.store.state.composers[this.props.id]) {
            throw new Error(`Already some store data in composer with id '${this.props.id}'`);
        }
        this.storeDispatch('createComposer', this.props.id, {
            attachmentLocalIds: this.props.initialAttachmentLocalIds || [],
        });
        document.addEventListener('click', this._onClickCaptureGlobal, true);
        document.addEventListener('dragenter', this._onDragenterCaptureGlobal, true);
        document.addEventListener('dragleave', this._onDragleaveCaptureGlobal, true);
        document.addEventListener('drop', this._onDropCaptureGlobal, true);
    }

    /**
     * @param {Object} nextProps
     * @param {string} nextProps.id
     */
    willUpdateProps(nextProps) {
        if (nextProps.id !== this.props.id) {
            throw new Error("'id' in props changed. Parent should keep same 'id' for same instance of component");
        }
    }

    patched() {
        if (this._focusCount !== this.props.focusCounter) {
            this.focus();
        }
        this._focusCount = this.props.focusCounter;
    }

    willUnmount() {
        this.storeDispatch('deleteComposer', this.props.id);
        $(window).off(this.fileuploadId, this._attachmentUploadedEventListener);
        document.removeEventListener('click', this._onClickCaptureGlobal, true);
        document.removeEventListener('dragenter', this._onDragenterCaptureGlobal, true);
        document.removeEventListener('dragleave', this._onDragleaveCaptureGlobal, true);
        document.removeEventListener('drop', this._onDropCaptureGlobal, true);
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @return {string}
     */
    get currentPartnerAvatar() {
        const avatar = this.env.session.uid > 0
            ? this.env.session.url('/web/image', {
                    field: 'image_128',
                    id: this.env.session.uid,
                    model: 'res.users',
                })
            : '/web/static/src/img/user_menu_avatar.png';
        return avatar;
    }

    /**
     * @return {boolean}
     */
    get hasFooter() {
        return this.storeProps.attachmentLocalIds.length > 0;
    }

    /**
     * @return {boolean}
     */
    get hasHeader() {
        return (
            (this.props.hasThreadName && this.storeProps.thread) ||
            (this.props.hasFollowers && !this.props.isLog)
        );
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    focus() {
        if (this.storeProps.isMobile) {
            this.el.scrollIntoView();
        }
        this._textInputRef.comp.focus();
    }

    focusout() {
        this._textInputRef.comp.focusout();
    }

    /**
     * @return {Object}
     */
    getState() {
        return {
            attachmentLocalIds: this.storeProps.attachmentLocalIds,
            textInputHtmlContent: this._textInputRef.comp.getHtmlContent(),
        };
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    async _postMessage() {
        // TODO: take suggested recipients into account
        try {
            await this.storeDispatch('postMessageOnThread', this.props.threadLocalId, {
                attachmentLocalIds: this.storeProps.attachmentLocalIds,
                htmlContent: this._textInputRef.comp.getHtmlContent(),
                isLog: this.props.isLog,
                threadCacheLocalId: this.props.threadCacheLocalId,
            });
            this._textInputRef.comp.reset();
            this.storeDispatch('unlinkAttachmentsFromComposer', this.props.id);
            // TODO: we might need to remove trigger and use the store to wait for
            // the post rpc to be done
            this.trigger('o-message-posted');
        } catch (err) {
            // ignore error
        }
    }

    /**
     * @private
     * @param {FileList|Array} files
     * @return {Promise}
     */
    async _uploadFiles(files) {
        for (const file of files) {
            const attachment = this.storeProps.attachmentLocalIds
                .map(localId => this.env.store.state.attachments[localId])
                .find(attachment =>
                    attachment.name === file.name && attachment.size === file.size);
            // if the file already exists, delete the file before upload
            if (attachment) {
                this.storeDispatch('unlinkAttachment', attachment.localId);
            }
        }
        for (const file of files) {
            const attachmentLocalId = this.storeDispatch('createAttachment', {
                filename: file.name,
                isTemporary: true,
                name: file.name,
            });
            this.storeDispatch('linkAttachmentToComposer', this.props.id, attachmentLocalId);
        }
        let formData = new window.FormData();
        formData.append('callback', this.fileuploadId);
        formData.append('csrf_token', core.csrf_token);
        formData.append('id', '0');
        formData.append('model', 'mail.compose.message');
        for (const file of files) {
            // removing existing key with blank data and appending again with
            // file info. In Safari, existing key will not be updated when
            // appended with new file.
            formData.delete('ufile');
            formData.append('ufile', file, file.name);
            const response = await window.fetch('/web/binary/upload_attachment', {
                body: formData,
                method: 'POST',
            });
            let html = await response.text();
            const template = document.createElement('template');
            template.innerHTML = html.trim();
            window.eval.call(window, template.content.firstChild.textContent);
        }
        this._fileInputRef.el.value = '';
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {jQuery.Event} ev
     * @param {...Object} fileData
     */
    _onAttachmentUploaded(ev, ...filesData) {
        for (const fileData of filesData) {
            const {
                error,
                filename,
                id,
                mimetype,
                name,
                size,
            } = fileData;
            if (error || !id) {
                this.env.do_warn(error);
                const temporaryAttachmentLocalId = this.env.store.state.temporaryAttachmentLocalIds[filename];
                if (temporaryAttachmentLocalId) {
                    this.storeDispatch('deleteAttachment', temporaryAttachmentLocalId);
                }
                return;
            }
            this.storeDispatch('createAttachment', {
                filename,
                id,
                mimetype,
                name,
                size,
            });
        }
    }

    /**
     * @private
     * @param {Event} ev
     */
    async _onChangeAttachment(ev) {
        await this._uploadFiles(ev.target.files);
    }

    /**
     * @private
     */
    _onClickAddAttachment() {
        this._fileInputRef.el.click();
        this.focus();
    }

    /**
     * Discards the composer when clicking away from the Inbox reply in discuss.
     * TODO SEB maybe move this in discuss.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickCaptureGlobal(ev) {
        // in discuss app: prevents discarding the composer when clicking away
        if (!this.props.isDiscardOnClickAway) {
            return;
        }
        // prevents discarding when clicking on self (on discuss and not on discuss)
        if (this.el.contains(ev.target)) {
            return;
        }
        // emoji popover is outside but should be considered inside
        if (this._emojisButtonRef.comp.isInsideEventTarget(ev.target)) {
            return;
        }
        this.trigger('o-discarded');
    }

    /**
     * @private
     */
    async _onClickFullComposer() {
        const attachmentIds = this.storeProps.attachmentLocalIds
            .map(localId => this.env.store.state.attachments[localId].res_id);

        const context = {
            // default_parent_id: this.id,
            default_body: this._textInput.comp.getHtmlContent(),
            default_attachment_ids: attachmentIds,
            // default_partner_ids: partnerIds,
            default_is_log: this.props.isLog,
            mail_post_autofollow: true,
        };

        // if (this.context.default_model && this.context.default_res_id) {
        //     context.default_model = this.context.default_model;
        //     context.default_res_id = this.context.default_res_id;
        // }

        const action = {
            type: 'ir.actions.act_window',
            res_model: 'mail.compose.message',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: context,
        };
        await this.env.do_action(action);
        this.trigger('o-full-composer-opened');
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickDiscard(ev) {
        this.trigger('o-discarded');
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickSend(ev) {
        if (
            this._textInput.comp.isEmpty() &&
            this.storeProps.attachmentLocalIds.length === 0
        ) {
            return;
        }
        ev.stopPropagation();
        this._postMessage();
    }

    /**
     * @private
     * @param {CustomEvent} ev
     */
    _onDiscardInput(ev) {
        this.trigger('o-discarded');
    }

    /**
     * Shows the dropzone when entering the browser window, to let the user know
     * where he can drop its file.
     * Avoids changing state when entering inner dropzones.
     *
     * @private
     * @param {DragEvent} ev
     */
    _onDragenterCaptureGlobal(ev) {
        if (this._dragCount === 0) {
            this.state.hasDropZone = true;
        }
        this._dragCount++;
    }

    /**
     * Hides the dropzone when leaving the browser window.
     * Avoids changing state when leaving inner dropzones.
     *
     * @private
     * @param {DragEvent} ev
     */
    _onDragleaveCaptureGlobal(ev) {
        this._dragCount--;
        if (this._dragCount === 0) {
            this.state.hasDropZone = false;
        }
    }

    /**
     * Hides the dropzone when dropping a file outside the dropzone.
     * This is necessary because the leave event is not triggered in that case.
     *
     * When dropping inside the dropzone, it will be hidden but only after the
     * file has been processed in `_onDropZoneFilesDropped`.
     *
     * @private
     * @param {DragEvent} ev
     */
    _onDropCaptureGlobal(ev) {
        this._dragCount = 0;
        if (!this._dropzoneRef.comp.contains(ev.target)) {
            this.state.hasDropZone = false;
        }
    }

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {FileList} ev.detail.files
     */
    _onDropZoneFilesDropped(ev) {
        this._uploadFiles(ev.detail.files);
        this.state.hasDropZone = false;
    }

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.unicode
     */
    _onEmojiSelection(ev) {
        this._textInputRef.comp.insertTextContent(ev.detail.unicode);
    }

    /**
     * @private
     */
    _onInputTextInput() {
        this.state.hasTextInputContent = !this._textInputRef.comp.isEmpty();
    }

    /**
     * @private
     * @param {CustomEvent} ev
     */
    _onPasteTextInput(ev) {
        if (
            !ev.clipboardData ||
            !ev.clipboardData.files
        ) {
            return;
        }
        this._uploadFiles(ev.clipboardData.files);
    }

    /**
     * @private
     * @param {CustomEvent} ev
     */
    _onTextInputKeydownEnter(ev) {
        if (
            this._textInputRef.comp.isEmpty() &&
            this.storeProps.attachmentLocalIds.length === 0
        ) {
            return;
        }
        this._postMessage();
    }

    /**
     * @private
     */
    _onShowLessSuggestedRecipients() {
        this.state.hasAllSuggestedRecipients = false;
    }

    /**
     * @private
     */
    _onShowMoreSuggestedRecipients() {
        this.state.hasAllSuggestedRecipients = true;
    }
}

Composer.components = {
    AttachmentList,
    DropZone,
    EmojisButton,
    TextInput,
};

Composer.defaultProps = {
    areButtonsInline: true,
    attachmentLocalIds: [],
    focusCounter: 0,
    hasCurrentPartnerAvatar: true,
    hasDiscardButton: false,
    hasFollowers: false,
    hasSendButton: true,
    hasThreadName: false,
    isDiscardOnClickAway: false,
    isExpandable: false,
    isFocusOnMount: false,
    isLog: false,
};

Composer.props = {
    areButtonsInline: {
        type: Boolean,
        optional: true,
    },
    attachmentLocalIds: {
        type: Array,
        element: String,
        optional: true,
    },
    attachmentsLayout: {
        type: String,
        optional: true,
    },
    focusCounter: {
        type: Number,
        optional: true,
    },
    hasCurrentPartnerAvatar: {
        type: Boolean,
        optional: true,
    },
    hasDiscardButton: {
        type: Boolean,
        optional: true,
    },
    hasFollowers: {
        type: Boolean,
        optional: true,
    },
    hasSendButton: {
        type: Boolean,
        optional: true,
    },
    hasThreadName: {
        type: Boolean,
        optional: true,
    },
    haveAttachmentsLabelForCardLayout: {
        type: Boolean,
        optional: true,
    },
    id: String,
    initialAttachmentLocalIds: {
        type: Array,
        element: String,
        optional: true,
    },
    initialTextInputHtmlContent: {
        type: String,
        optional: true,
    },
    isDiscardOnClickAway: {
        type: Boolean,
        optional: true,
    },
    isExpandable: {
        type: Boolean,
        optional: true,
    },
    isFocusOnMount: {
        type: Boolean,
        optional: true,
    },
    isLog: {
        type: Boolean,
        optional: true,
    },
    threadCacheLocalId: {
        type: String,
        optional: true,
    },
    threadLocalId: {
        type: String,
        optional: true,
    },
};

Composer.template = 'mail.component.Composer';

return Composer;

});
