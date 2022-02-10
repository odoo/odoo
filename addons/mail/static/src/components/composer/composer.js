/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { useDragVisibleDropZone } from '@mail/component_hooks/use_drag_visible_dropzone/use_drag_visible_dropzone';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { isEventHandled } from '@mail/utils/utils';

const { Component } = owl;

export class Composer extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        this.isDropZoneVisible = useDragVisibleDropZone();
        useComponentToModel({ fieldName: 'component', modelName: 'ComposerView' });
        useRefToModel({ fieldName: 'buttonEmojisRef', modelName: 'ComposerView', refName: 'buttonEmojis' });
        this._onDropZoneFilesDropped = this._onDropZoneFilesDropped.bind(this);
        this._onComposerTextInputSendShortcut = this._onComposerTextInputSendShortcut.bind(this);
        this._onPasteTextInput = this._onPasteTextInput.bind(this);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {ComposerView}
     */
    get composerView() {
        return this.messaging && this.messaging.models['ComposerView'].get(this.props.localId);
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
        this.composerView.fileUploader.openBrowserFileUploader();
        if (!this.messaging.device.isMobileDevice) {
            this.composerView.update({ doFocus: true });
        }
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
     * @param {Object} detail
     * @param {FileList} detail.files
     */
    async _onDropZoneFilesDropped(detail) {
        await this.composerView.fileUploader.uploadFiles(detail.files);
        this.isDropZoneVisible.value = false;
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
     * @param {CustomEvent} ev
     */
    async _onPasteTextInput(ev) {
        if (!ev.clipboardData || !ev.clipboardData.files) {
            return;
        }
        await this.composerView.fileUploader.uploadFiles(ev.clipboardData.files);
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
        localId: String,
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
        hasMentionSuggestionsBelowPosition: {
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
        hasThreadTyping: {
            type: Boolean,
            optional: true,
        },
        showAttachmentsExtensions: {
            type: Boolean,
            optional: true,
        },
        showAttachmentsFilenames: {
            type: Boolean,
            optional: true,
        },
        isCompact: {
            type: Boolean,
            optional: true,
        },
        isExpandable: {
            type: Boolean,
            optional: true,
        },
    },
    template: 'mail.Composer',
});

registerMessagingComponent(Composer);
