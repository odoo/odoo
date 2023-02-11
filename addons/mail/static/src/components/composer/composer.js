/** @odoo-module **/

import { useDragVisibleDropZone } from '@mail/component_hooks/use_drag_visible_dropzone/use_drag_visible_dropzone';
import { registerMessagingComponent } from '@mail/utils/messaging_component';
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
         * Reference of the text input component. Useful to save state in store
         * before inserting emoji.
         */
        this._textInputRef = useRef('textInput');
        this._onClickCaptureGlobal = this._onClickCaptureGlobal.bind(this);
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
     * @returns {mail.composer_view}
     */
    get composerView() {
        return this.messaging && this.messaging.models['mail.composer_view'].get(this.props.composerViewLocalId);
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
        if (emojisPopover && emojisPopover.contains(node)) {
            return true;
        }
        return Boolean(this.el && this.el.contains(node));
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
     * Determine whether composer should display a footer.
     *
     * @returns {boolean}
     */
    get hasFooter() {
        if (!this.composerView) {
            return false;
        }
        return (
            this.props.hasThreadTyping ||
            this.composerView.composer.attachments.length > 0 ||
            this.composerView.messageViewInEditing ||
            !this.props.isCompact
        );
    }

    /**
     * Determine whether the composer should display a header.
     *
     * @returns {boolean}
     */
    get hasHeader() {
        if (!this.composerView) {
            return false;
        }
        return (
            (this.props.hasThreadName && this.composerView.composer.thread) ||
            (this.props.hasFollowers && !this.composerView.composer.isLog) ||
            this.composerView.threadView && this.composerView.threadView.replyingToMessageView
        );
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
    _postMessage() {
        if (!this.composerView.composer.canPostMessage) {
            if (this.composerView.composer.hasUploadingAttachment) {
                this.env.services['notification'].notify({
                    message: this.env._t("Please wait while the file is uploading."),
                    type: 'warning',
                });
            }
            return;
        }
        if (this.composerView.messageViewInEditing) {
            this.composerView.updateMessage();
            return;
        }
        this.composerView.postMessage();
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
        if (!this.messaging.device.isMobileDevice) {
            this.composerView.update({ doFocus: true });
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
        if (!this.composerView) {
            return;
        }
        this.composerView.discard();
    }

    /**
     * Called when clicking on "expand" button.
     *
     * @private
     */
    _onClickFullComposer() {
        this.composerView.openFullComposer();
    }

    /**
     * Called when clicking on "discard" button.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickDiscard(ev) {
        this.composerView.discard();
    }

    /**
     * Called when clicking on "send" button.
     *
     * @private
     */
    _onClickSend() {
        this._postMessage();
        this.composerView.update({ doFocus: true });
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
        this.composerView.insertIntoTextInput(ev.detail.unicode);
        if (!this.messaging.device.isMobileDevice) {
            this.composerView.update({ doFocus: true });
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
            this.composerView.discard();
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
                this.composerView.update({ doFocus: true });
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
        isExpandable: false,
    },
    props: {
        composerViewLocalId: String,
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
