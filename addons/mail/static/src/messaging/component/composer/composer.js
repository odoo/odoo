odoo.define('mail.messaging.component.Composer', function (require) {
'use strict';

const components = {
    AttachmentList: require('mail.messaging.component.AttachmentList'),
    DropZone: require('mail.messaging.component.DropZone'),
    EmojisButton: require('mail.messaging.component.EmojisButton'),
    FileUploader: require('mail.messaging.component.FileUploader'),
    TextInput: require('mail.messaging.component.ComposerTextInput'),
};
const useDragVisibleDropZone = require('mail.messaging.component_hook.useDragVisibleDropZone');
const useStore = require('mail.messaging.component_hook.useStore');
const mailUtils = require('mail.utils');

const { Component } = owl;
const { useRef } = owl.hooks;

class Composer extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this.isDropZoneVisible = useDragVisibleDropZone();
        useStore(props => {
            const composer = this.env.entities.Composer.get(props.composerLocalId);
            return {
                composer,
                isDeviceMobile: this.env.messaging.device.isMobile,
                thread: composer ? composer.thread : undefined,
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
        // to focus if the prop changes
        this._lastComposer = undefined;
        this._onClickCaptureGlobal = this._onClickCaptureGlobal.bind(this);
    }

    mounted() {
        this._lastComposer = this.composer;
        if (this.props.isFocusOnMount) {
            this.focus();
        }
        document.addEventListener('click', this._onClickCaptureGlobal, true);
    }

    patched() {
        // focus when changing composer
        if (
            this.props.isFocusOnMount &&
            this._lastComposer !== this.composer
        ) {
            this.focus();
        }
        this._lastComposer = this.composer;
    }

    willUnmount() {
        document.removeEventListener('click', this._onClickCaptureGlobal, true);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.messaging.entity.Composer}
     */
    get composer() {
        return this.env.entities.Composer.get(this.props.composerLocalId);
    }

    /**
     * Get the current partner image URL.
     *
     * @returns {string}
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
     * Focus the composer.
     */
    focus() {
        if (this.env.messaging.device.isMobile) {
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

    /**
     * Determine whether composer should display a footer.
     *
     * @returns {boolean}
     */
    get hasFooter() {
        return this.composer.attachments.length > 0 || !this.props.isCompact;
    }

    /**
     * Determine whether the composer should display a header.
     *
     * @returns {boolean}
     */
    get hasHeader() {
        return (
            (this.props.hasThreadName && this.composer.thread) ||
            (this.props.hasFollowers && !this.props.isLog)
        );
    }

    /**
     * Get an object which is passed to FileUploader component to be used when
     * creating attachment.
     *
     * @returns {Object}
     */
    get newAttachmentExtraData() {
        return { composers: [this.composer] };
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
        await this.composer.postMessage({ isLog: this.props.isLog });
        // TODO: we might need to remove trigger and use the store to wait for the post rpc to be done
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
        this.composer.discard();
    }

    /**
     * Called when clicking on "expand" button.
     *
     * @private
     */
    async _onClickFullComposer() {
        const attachmentIds = this.composer.attachments.map(attachment => attachment.res_id);

        const context = {
            // default_parent_id: this.id,
            default_body: mailUtils.escapeAndCompactTextContent(this._textInputRef.comp.getContent()),
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
        this.composer.discard();
    }

    /**
     * Called when clicking on "send" button.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickSend(ev) {
        if (
            !this.composer.textInputContent &&
            this.composer.attachments.length === 0
        ) {
            return;
        }
        ev.stopPropagation();
        this._postMessage();
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
        ev.stopPropagation();
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
        ev.stopPropagation();
        this._textInputRef.comp.saveStateInStore();
        this.composer.insertIntoTextInput(ev.detail.unicode);
        this._textInputRef.comp.focus();
    }

    /**
     * @private
     */
    _onInputTextInput() {
        this._textInputRef.comp.saveStateInStore();
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
        ev.stopPropagation();
        // TODO SEB this is the same code as _onClickSend
        if (
            !this.composer.textInputContent &&
            this.composer.attachments.length === 0
        ) {
            return;
        }
        this._postMessage();
    }

}

Object.assign(Composer, {
    components,
    defaultProps: {
        attachmentLocalIds: [],
        hasCurrentPartnerAvatar: true,
        hasDiscardButton: false,
        hasFollowers: false,
        hasSendButton: true,
        hasTextInputSendOnEnterEnabled: true,
        hasThreadName: false,
        isCompact: true,
        isDiscardOnClickAway: false,
        isExpandable: false,
        isFocusOnMount: false,
        isLog: false,
    },
    props: {
        attachmentLocalIds: {
            type: Array,
            element: String,
        },
        attachmentsDetailsMode: {
            type: String,
            optional: true,
        },
        composerLocalId: String,
        hasCurrentPartnerAvatar: Boolean,
        hasDiscardButton: Boolean,
        hasFollowers: Boolean,
        hasSendButton: Boolean,
        hasTextInputSendOnEnterEnabled: Boolean,
        hasThreadName: Boolean,
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
        isCompact: Boolean,
        isDiscardOnClickAway: Boolean,
        isExpandable: Boolean,
        isFocusOnMount: Boolean,
        isLog: Boolean,
    },
    template: 'mail.messaging.component.Composer',
});

return Composer;

});
