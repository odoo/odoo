/** @odoo-module **/

import { useDragVisibleDropZone } from '@mail/component_hooks/use_drag_visible_dropzone/use_drag_visible_dropzone';
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';
import { useUpdate } from '@mail/component_hooks/use_update/use_update';
import { replace } from '@mail/model/model_field_command';
import {
    isEventHandled,
    markEventHandled,
} from '@mail/utils/utils';

const { Component } = owl;
const { useRef } = owl.hooks;

export class Composer extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this.isDropZoneVisible = useDragVisibleDropZone();
        useUpdate({ func: () => this._update() });
        /**
         * Reference of the emoji popover. Useful to include emoji popover as
         * contained "inside" the composer.
         */
        this._emojisPopoverRef = useRef('emojisPopover');
        /**
         * Reference of the file uploader.
         * Useful to programmatically prompts the browser file uploader.
         */
        this._fileUploaderRef = useRef('fileUploader');
        /**
         * The main role of this component (composer_text_input) is to connect the Legancy Widget (composer_wysiwyg)
         * to the OWL component (composer).
         */
        this._textInputRef = useRef('textInput');
        this._onClickCaptureGlobal = this._onClickCaptureGlobal.bind(this);
    }

    setup() {
        super.setup();
        useRefToModel({ fieldName: 'textInputRef', modelName: 'mail.composer', propNameAsRecordLocalId: 'composerLocalId', refName: 'textInput' });
    }

    mounted() {
        document.addEventListener('click', this._onClickCaptureGlobal, true);
    }

    willUnmount() {
        document.removeEventListener('click', this._onClickCaptureGlobal, true);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.composer}
     */
    get composer() {
        return this.messaging && this.messaging.models['mail.composer'].get(this.props.composerLocalId);
    }

    /**
     * Returns whether the given node is self or a children of self, including
     * the emoji popover.
     *
     * @param {Node} node
     * @returns {boolean}
     */
    contains(node) {
        // emoji popover is outside but should be considered inside
        const emojisPopover = this._emojisPopoverRef.comp;
        const wysiwyg = this._textInputRef.comp._wysiwygRef;
        if (emojisPopover && emojisPopover.contains(node)) {
            return true;
        }
        // wysiwyg, including toolbar should be considered inside
        if (wysiwyg && wysiwyg.contains(node)) {
            return true;
        }
        return this.el.contains(node);
    }

    /**
     * Get the current partner image URL.
     *
     * @returns {string}
     */
    get currentPartnerAvatar() {
        const avatar = this.messaging.currentUser
            ? this.env.session.url('/web/image', {
                    field: 'avatar_128',
                    id: this.messaging.currentUser.id,
                    model: 'res.users',
                })
            : '/web/static/img/user_menu_avatar.png';
        return avatar;
    }

    /**
     * Focus the composer.
     */
    focus() {
        if (this.messaging.device.isMobile) {
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
        if (!this.composer) {
            return false;
        }
        return (
            this.props.hasThreadTyping ||
            this.composer.attachments.length > 0 ||
            this.composer.messageInEditing ||
            !this.props.isCompact
        );
    }

    /**
     * Determine whether the composer should display a header.
     *
     * @returns {boolean}
     */
    get hasHeader() {
        return (
            (this.props.hasThreadName && this.composer.thread) ||
            (this.props.hasFollowers && !this.composer.isLog)
        );
    }

    /**
     * Get an object which is passed to FileUploader component to be used when
     * creating attachment.
     *
     * @returns {Object}
     */
    get newAttachmentExtraData() {
        return {
            composers: replace(this.composer),
        };
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Post a message in the composer on related thread.
     *
     * Posting of the message could be aborted if it cannot be posted like if there are attachments
     * currently uploading or if there is no text content and no attachments.
     *
     * @private
     */
    async _postMessage() {
        if (!this.composer.canPostMessage) {
            if (this.composer.hasUploadingAttachment) {
                this.env.services['notification'].notify({
                    message: this.env._t("Please wait while the file is uploading."),
                    type: 'warning',
                });
            }
            return;
        }
        if (this.composer.messageInEditing && this.composer.messageInEditing.isEditing) {
            await this.composer.updateMessage();
            return;
        }
        await this.composer.postMessage();
        this._textInputRef.comp._wysiwygRef.clear();
        // TODO: we might need to remove trigger and use the store to wait for the post rpc to be done
        // task-2252858
        this.trigger('o-message-posted');
    }

    /**
     * @private
     */
    _update() {
        if (this.props.isDoFocus) {
            this.focus();
        }
        if (!this.composer) {
            return;
        }
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
        if (!this.env.device.isMobile) {
            this.focus();
        }
    }

    /**
     * Discards the composer when clicking away.
     *
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickCaptureGlobal(ev) {
        if (this.contains(ev.target)) {
            return;
        }
        // Let event be handled by bubbling handlers first
        await new Promise(this.env.browser.setTimeout);
        if (isEventHandled(ev, 'MessageActionList.replyTo')) {
            return;
        }
        if (!this.composer) {
            return;
        }
        this.composer.discard();
    }

    /**
     * Called when clicking on "expand" button.
     *
     * @private
     */
    _onClickFullComposer() {
        this.composer.openFullComposer();
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
     */
    _onClickSend() {
        this._postMessage();
        this.focus();
    }

    /**
     * @private
     */
    _onComposerSuggestionClicked() {
        this.focus();
    }

    /**
     * @private
     */
    _onComposerTextInputSendShortcut() {
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
     * Handles `o-emoji-selection` event from the emoji popover.
     *
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.unicode
     */
    _onEmojiSelection(ev) {
        ev.stopPropagation();
        this._textInputRef.comp.saveStateInStore();
        // This will call the legacy wysiwyg to update the content, and afterwards,
        // updating the composer.textInputContent automaticlly.
        this._textInputRef.comp.insertIntoTextInput(ev.detail.unicode);
        if (!this.env.device.isMobile) {
            this.focus();
        }
    }

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydown(ev) {
        if (ev.key === 'Escape') {
            if (isEventHandled(ev, 'ComposerTextInput.closeSuggestions')) {
                return;
            }
            if (isEventHandled(ev, 'Composer.closeEmojisPopover')) {
                return;
            }
            ev.preventDefault();
            this.composer.discard();
        }
    }

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydownEmojiButton(ev) {
        if (ev.key === 'Escape') {
            if (this._emojisPopoverRef.comp) {
                this._emojisPopoverRef.comp.close();
                this.focus();
                markEventHandled(ev, 'Composer.closeEmojisPopover');
            }
        }
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

}

Object.assign(Composer, {
    defaultProps: {
        hasCurrentPartnerAvatar: true,
        hasDiscardButton: false,
        hasFollowers: false,
        hasSendButton: true,
        hasThreadName: false,
        hasThreadTyping: false,
        isCompact: true,
        isDoFocus: false,
        isExpandable: false,
    },
    props: {
        attachmentsDetailsMode: {
            type: String,
            optional: true,
        },
        composerLocalId: String,
        hasCurrentPartnerAvatar: Boolean,
        hasDiscardButton: Boolean,
        hasFollowers: Boolean,
        hasMentionSuggestionsBelowPosition: {
            type: Boolean,
            optional: true,
        },
        hasSendButton: Boolean,
        hasThreadName: Boolean,
        hasThreadTyping: Boolean,
        /**
         * Determines whether this should become focused.
         */
        isDoFocus: Boolean,
        showAttachmentsExtensions: {
            type: Boolean,
            optional: true,
        },
        showAttachmentsFilenames: {
            type: Boolean,
            optional: true,
        },
        isCompact: Boolean,
        isExpandable: Boolean,
        /**
         * If set, keyboard shortcuts from text input to send message.
         * If not set, will use default values from `ComposerTextInput`.
         */
        textInputSendShortcuts: {
            type: Array,
            element: String,
            optional: true,
        },
    },
    template: 'mail.Composer',
});

registerMessagingComponent(Composer, { propsCompareDepth: { textInputSendShortcuts: 1 } });
