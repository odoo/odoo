odoo.define('mail/static/src/components/composer/composer.js', function (require) {
'use strict';

const components = {
    AttachmentList: require('mail/static/src/components/attachment_list/attachment_list.js'),
    ComposerSuggestedRecipientList: require('mail/static/src/components/composer_suggested_recipient_list/composer_suggested_recipient_list.js'),
    DropZone: require('mail/static/src/components/drop_zone/drop_zone.js'),
    EmojisPopover: require('mail/static/src/components/emojis_popover/emojis_popover.js'),
    FileUploader: require('mail/static/src/components/file_uploader/file_uploader.js'),
    TextInput: require('mail/static/src/components/composer_text_input/composer_text_input.js'),
    ThreadTextualTypingStatus: require('mail/static/src/components/thread_textual_typing_status/thread_textual_typing_status.js'),
};
const useDragVisibleDropZone = require('mail/static/src/component_hooks/use_drag_visible_dropzone/use_drag_visible_dropzone.js');
const useShouldUpdateBasedOnProps = require('mail/static/src/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props.js');
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');
const useUpdate = require('mail/static/src/component_hooks/use_update/use_update.js');
const {
    isEventHandled,
    markEventHandled,
} = require('mail/static/src/utils/utils.js');

const { Component } = owl;
const { useRef } = owl.hooks;

class Composer extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this.isDropZoneVisible = useDragVisibleDropZone();
        useShouldUpdateBasedOnProps({
            compareDepth: {
                textInputSendShortcuts: 1,
            },
        });
        useStore(props => {
            const composer = this.env.models['mail.composer'].get(props.composerLocalId);
            const thread = composer && composer.thread;
            return {
                composer,
                composerAttachments: composer ? composer.attachments : [],
                composerCanPostMessage: composer && composer.canPostMessage,
                composerHasFocus: composer && composer.hasFocus,
                composerIsLog: composer && composer.isLog,
                composerSubjectContent: composer && composer.subjectContent,
                isDeviceMobile: this.env.messaging.device.isMobile,
                thread,
                threadChannelType: thread && thread.channel_type, // for livechat override
                threadDisplayName: thread && thread.displayName,
                threadMassMailing: thread && thread.mass_mailing,
                threadModel: thread && thread.model,
                threadName: thread && thread.name,
            };
        }, {
            compareDepth: {
                composerAttachments: 1,
            },
        });
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
         * Reference of the text input component.
         */
        this._textInputRef = useRef('textInput');
        /**
         * Reference of the subject input. Useful to set content.
         */
        this._subjectRef = useRef('subject');
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
     * @returns {mail.composer}
     */
    get composer() {
        return this.env.models['mail.composer'].get(this.props.composerLocalId);
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
        return this.el.contains(node);
    }

    /**
     * Get the current partner image URL.
     *
     * @returns {string}
     */
    get currentPartnerAvatar() {
        const avatar = this.env.messaging.currentUser
            ? this.env.session.url('/web/image', {
                    field: 'image_128',
                    id: this.env.messaging.currentUser.id,
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
        return (
            this.props.hasThreadTyping ||
            this.composer.attachments.length > 0 ||
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
            composers: [['replace', this.composer]],
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
        await this.composer.postMessage();
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
        if (this._subjectRef.el) {
            this._subjectRef.el.value = this.composer.subjectContent;
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
    _onClickCaptureGlobal(ev) {
        if (this.contains(ev.target)) {
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
        if (!this.env.device.isMobile) {
            this.focus();
        }
    }

    /**
     * @private
     */
    _onInputSubject() {
        this.composer.update({ subjectContent: this._subjectRef.el.value });
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
    components,
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

return Composer;

});
