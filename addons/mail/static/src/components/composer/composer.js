/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { useDragVisibleDropZone } from '@mail/component_hooks/use_drag_visible_dropzone/use_drag_visible_dropzone';
import { useModels } from '@mail/component_hooks/use_models/use_models';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';
import { useShouldUpdateBasedOnProps } from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import { useUpdate } from '@mail/component_hooks/use_update/use_update';
import { AttachmentList } from '@mail/components/attachment_list/attachment_list';
import { ComposerSuggestedRecipientList } from '@mail/components/composer_suggested_recipient_list/composer_suggested_recipient_list';
import { ComposerTextInput } from '@mail/components/composer_text_input/composer_text_input';
import { DropZone } from '@mail/components/drop_zone/drop_zone';
import { EmojisPopover } from '@mail/components/emojis_popover/emojis_popover';
import { FileUploader } from '@mail/components/file_uploader/file_uploader';
import { ThreadTextualTypingStatus } from '@mail/components/thread_textual_typing_status/thread_textual_typing_status';
import { replace } from '@mail/model/model_field_command';

const { Component } = owl;
const { useRef } = owl.hooks;

const components = {
    AttachmentList,
    ComposerSuggestedRecipientList,
    ComposerTextInput,
    DropZone,
    EmojisPopover,
    FileUploader,
    ThreadTextualTypingStatus,
};

export class Composer extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this.isDropZoneVisible = useDragVisibleDropZone();
        useRefToModel({ fieldName: 'fileUploaderRef', modelName: 'mail.composer', propNameAsRecordLocalId: 'composerLocalId', refName: 'fileUploader' });
        useShouldUpdateBasedOnProps({
            compareDepth: {
                textInputSendShortcuts: 1,
            },
        });
        useModels();
        useComponentToModel({ fieldName: 'component', modelName: 'mail.composer', propNameAsRecordLocalId: 'composerLocalId' });
        useUpdate({ func: () => this._update() });
        useRefToModel({ fieldName: 'textInputRef', modelName: 'mail.composer', propNameAsRecordLocalId: 'composerLocalId', refName: 'textInput' });
        useRefToModel({ fieldName: 'emojisPopoverRef', modelName: 'mail.composer', propNameAsRecordLocalId: 'composerLocalId', refName: 'emojisPopover' });
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
                    field: 'avatar_128',
                    id: this.env.messaging.currentUser.id,
                    model: 'res.users',
                })
            : '/web/static/img/user_menu_avatar.png';
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
            composers: replace(this.composer),
        };
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

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
