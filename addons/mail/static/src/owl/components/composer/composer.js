odoo.define('mail.component.Composer', function (require) {
'use strict';

const AttachmentList = require('mail.component.AttachmentList');
const DropZone = require('mail.component.DropZone');
const EmojisButton = require('mail.component.EmojisButton');
const FileUploader = require('mail.component.FileUploader');
const TextInput = require('mail.component.ComposerTextInput');
const useDragVisibleDropZone = require('mail.hooks.useDragVisibleDropZone');

const { Component } = owl;
const { useDispatch, useGetters, useRef, useState, useStore } = owl.hooks;

class Composer extends Component {

    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.state = useState({
            /**
             * Determine whether there are some text content. Useful to prevent
             * user to post something when there are no text content and no
             * attachments.
             */
            hasTextInputContent: false,
        });
        this.isDropZoneVisible = useDragVisibleDropZone();
        this.storeDispatch = useDispatch();
        this.storeGetters = useGetters();
        this.storeProps = useStore((state, props) => {
            const composer = state.composers[props.composerLocalId];
            return {
                composer,
                isMobile: state.isMobile,
                thread: state.threads[composer.threadLocalId],
            };
        });
        /**
         * Reference of the emoji button. Useful to include emoji popover as
         * click "inside" the composer for the prop `isDiscardOnClickAway`.
         */
        this._emojisButtonRef = useRef('emojisButton');
        /**
         * Reference of the file uploader.
         * Useful to programmatically prompts the browser file uploader.
         */
        this._fileUploaderRef = useRef('fileUploader');
        /**
         * Reference of the text input component.
         */
        this._textInputRef = useRef('textInput');
        /**
         * Tracked focus counter from props. Useful to determine whether it
         * should auto focus this composer when patched.
         */
        this._focusCount = 0;
        this._onClickCaptureGlobal = this._onClickCaptureGlobal.bind(this);
    }

    mounted() {
        if (this.props.isFocusOnMount) {
            this.focus();
        }
        document.addEventListener('click', this._onClickCaptureGlobal, true);
    }

    patched() {
        if (this._focusCount !== this.props.focusCounter) {
            this.focus();
        }
        this._focusCount = this.props.focusCounter;
    }

    willUnmount() {
        document.removeEventListener('click', this._onClickCaptureGlobal, true);
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * Get the current partner image URL.
     *
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
     * Determine whether composer should display a footer.
     *
     * @return {boolean}
     */
    get hasFooter() {
        return this.storeProps.composer.attachmentLocalIds.length > 0;
    }

    /**
     * Determine whether the composer should display a header.
     *
     * @return {boolean}
     */
    get hasHeader() {
        return (
            (this.props.hasThreadName && this.storeProps.thread) ||
            (this.props.hasFollowers && !this.props.isLog)
        );
    }

    /**
     * Get an object which is passed to FileUploader component to be used when
     * creating attachment.
     *
     * @return {Object}
     */
    get newAttachmentExtraData() {
        return { composerLocalId: this.props.composerLocalId };
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Focus the composer.
     */
    focus() {
        if (this.storeProps.isMobile) {
            this.el.scrollIntoView();
        }
        this._textInputRef.comp.focus();
    }

    /**
     * Focusout the composer.
     */
    focusout() {
        this._textInputRef.comp.focusout();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Post a message in the composer on related thread.
     *
     * @private
     */
    async _postMessage() {
        // TODO: take suggested recipients into account
        this.storeDispatch('postMessage', this.props.composerLocalId, {
            htmlContent: this._textInputRef.comp.getHtmlContent(),
            isLog: this.props.isLog,
        });
        this._textInputRef.comp.reset();
        this.storeDispatch('unlinkAttachmentsFromComposer', this.props.composerLocalId);
        // TODO: we might need to remove trigger and use the store to wait for
        // the post rpc to be done
        this.trigger('o-message-posted');
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when clicking on attachment button.
     *
     * @private
     */
    _onClickAddAttachment() {
        this._fileUploaderRef.comp.openBrowserFileUploader();
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
     * Called when clicking on "expand" button.
     *
     * @private
     */
    async _onClickFullComposer() {
        const attachmentIds = this.storeProps.composer.attachmentLocalIds
            .map(localId => this.env.store.state.attachments[localId].res_id);

        const context = {
            // default_parent_id: this.id,
            default_body: this._textInputRef.comp.getHtmlContent(),
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
     * Called when clicking on "discard" button.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickDiscard(ev) {
        this.trigger('o-discarded');
    }

    /**
     * Called when clicking on "send" button.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickSend(ev) {
        if (
            this._textInputRef.comp.isEmpty() &&
            this.storeProps.composer.attachmentLocalIds.length === 0
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
     * Called when some files have been dropped in the dropzone.
     *
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {FileList} ev.detail.files
     */
    async _onDropZoneFilesDropped(ev) {
        await this._fileUploaderRef.comp.uploadFiles(ev.detail.files);
        this.isDropZoneVisible.value = false;
    }

    /**
     * Called when selection an emoji from the emoji popover (from the emoji
     * button).
     *
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
    async _onPasteTextInput(ev) {
        if (!ev.clipboardData || !ev.clipboardData.files) {
            return;
        }
        await this._fileUploaderRef.comp.uploadFiles(ev.clipboardData.files);
    }

    /**
     * @private
     * @param {CustomEvent} ev
     */
    _onTextInputKeydownEnter(ev) {
        if (
            this._textInputRef.comp.isEmpty() &&
            this.storeProps.composer.attachmentLocalIds.length === 0
        ) {
            return;
        }
        this._postMessage();
    }

}

Composer.components = { AttachmentList, DropZone, EmojisButton, FileUploader, TextInput };

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
    },
    attachmentLocalIds: {
        type: Array,
        element: String,
    },
    attachmentsDetailsMode: {
        type: String,
        optional: true,
    },
    composerLocalId: String,
    focusCounter: {
        type: Number,
    },
    hasCurrentPartnerAvatar: {
        type: Boolean,
    },
    hasDiscardButton: {
        type: Boolean,
    },
    hasFollowers: {
        type: Boolean,
    },
    hasSendButton: {
        type: Boolean,
    },
    hasThreadName: {
        type: Boolean,
    },
    showAttachmentsExtensions: {
        type: Boolean,
        optional: true,
    },
    showAttachmentsFilenames: {
        type: Boolean,
        optional: true,
    },
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
    },
    isExpandable: {
        type: Boolean,
    },
    isFocusOnMount: {
        type: Boolean,
    },
    isLog: {
        type: Boolean,
    },
};

Composer.template = 'mail.component.Composer';

return Composer;

});
