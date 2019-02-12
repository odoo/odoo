odoo.define('mail.component.Composer', function (require) {
'use strict';

const AttachmentList = require('mail.component.AttachmentList');
const DropZone = require('mail.component.DropZone');
const EmojisButton = require('mail.component.EmojisButton');
const TextInput = require('mail.component.ComposerTextInput');

const core = require('web.core');

class Composer extends owl.store.ConnectedComponent {

    /**
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
        this._emojisButtonRef = owl.hooks.useRef('emojisButton');
        this._fileInputRef = owl.hooks.useRef('fileInput');
        /**
         * Tracked focus counter from props. Useful to determine whether it
         * should auto focus this composer when patched.
         */
        this._focusCounter = 0;
        this._globalCaptureClickEventListener = ev => this._onClickCaptureGlobal(ev);
        this._globalDragleaveListener = ev => this._onDragleaveGlobal(ev);
        this._globalDragoverListener = ev => this._onDragoverGlobal(ev);
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
        this.dispatch('createComposer', this.props.id, {
            attachmentLocalIds: this.props.initialAttachmentLocalIds || [],
        });
        document.addEventListener('click', this._globalCaptureClickEventListener, true);
        document.addEventListener('dragleave', this._globalDragleaveListener);
        document.addEventListener('dragover', this._globalDragoverListener);
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
        if (this._focusCounter !== this.props.focusCounter) {
            this.focus();
        }
        this._focusCounter = this.props.focusCounter;
    }

    willUnmount() {
        this.dispatch('deleteComposer', this.props.id);
        $(window).off(this.fileuploadId, this._attachmentUploadedEventListener);
        document.removeEventListener('click', this._globalCaptureClickEventListener, true);
        document.removeEventListener('dragleave', this._globalDragleaveListener);
        document.removeEventListener('dragover', this._globalDragoverListener);
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
            await this.dispatch('postMessageOnThread', this.props.threadLocalId, {
                attachmentLocalIds: this.storeProps.attachmentLocalIds,
                htmlContent: this._textInputRef.comp.getHtmlContent(),
                isLog: this.props.isLog,
                threadCacheLocalId: this.props.threadCacheLocalId,
            });
            this._textInputRef.comp.reset();
            this.dispatch('unlinkAttachmentsFromComposer', this.props.id);
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
                this.dispatch('unlinkAttachment', attachment.localId);
            }
        }
        for (const file of files) {
            const attachmentLocalId = this.dispatch('createAttachment', {
                filename: file.name,
                isTemporary: true,
                name: file.name,
            });
            this.dispatch('linkAttachmentToComposer', this.props.id, attachmentLocalId);
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
                    this.dispatch('deleteAttachment', temporaryAttachmentLocalId);
                }
                return;
            }
            this.dispatch('createAttachment', {
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
     * @private
     * @param {MouseEvent} ev
     */
    _onClickCaptureGlobal(ev) {
        if (!this.props.isDiscardOnClickAway) {
            return;
        }
        if (ev.target.closest(`[data-id="${this.props.id}"]`)) {
            return;
        }
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
     * @private
     * @param {DragEvent} ev
     */
    _onDragleaveGlobal(ev) {
        if (
            ev.clientX <= 0 ||
            ev.clientY <= 0 ||
            ev.clientX >= window.innerWidth ||
            ev.clientY >= window.innerHeight
        ) {
            this.state.hasDropZone = false;
        }
    }

    /**
     * @private
     * @param {DragEvent} ev
     */
    _onDragoverGlobal(ev) {
        ev.preventDefault();
        this.state.hasDropZone = true;
    }

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {FileList} ev.detail.files
     */
    _onDropZoneFilesDropped(ev) {
        this.state.hasDropZone = false;
        this._uploadFiles(ev.detail.files);
    }

    /**
     * @private
     * @param {DragEvent} ev
     */
    _onDropZoneOutsideDrop() {
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

/**
 * @param {Object} state
 * @param {Object} ownProps
 * @param {string} ownProps.id
 * @param {Object[]} [ownProps.suggestedRecipients=[]]
 * @param {string} [ownProps.threadLocalId]
 */
Composer.mapStoreToProps = function (
    state,
    {
        id,
        suggestedRecipients=[],
        threadLocalId,
    }
) {
    const storeComposerState = _.defaults({
        ...state.composers[id],
    }, {
        attachmentLocalIds: [],
    });
    return {
        ...storeComposerState,
        fullSuggestedRecipients: suggestedRecipients.map(recipient => {
            return {
                ...recipient,
                partner: state.partners[recipient.partnerLocalId],
            };
        }),
        isMobile: state.isMobile,
        thread: state.threads[threadLocalId],
    };
};

Composer.props = {
    areButtonsInline: Boolean,
    attachmentsLayout: {
        type: String,
        optional: true,
    },
    focusCounter: Number,
    hasCurrentPartnerAvatar: Boolean,
    hasDiscardButton: Boolean,
    hasFollowers: Boolean,
    hasSendButton: Boolean,
    hasThreadName: Boolean,
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
    isDiscardOnClickAway: Boolean,
    isExpandable: Boolean,
    isFocusOnMount: Boolean,
    isLog: Boolean,
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
