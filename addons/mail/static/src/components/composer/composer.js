/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useDragVisibleDropZone } from '@mail/component_hooks/use_drag_visible_dropzone';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
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
        this.composerView.sendMessage();
        this.composerView.update({ doFocus: true });
    }

    /**
     * @private
     */
    _onComposerTextInputSendShortcut() {
        this.composerView.sendMessage();
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
        hasSendButton: true,
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
        hasMentionSuggestionsBelowPosition: {
            type: Boolean,
            optional: true,
        },
        hasSendButton: {
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
        isExpandable: {
            type: Boolean,
            optional: true,
        },
    },
    template: 'mail.Composer',
});

registerMessagingComponent(Composer);
