/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'Dialog',
    identifyingMode: 'xor',
    lifecycleHooks: {
        _created() {
            document.addEventListener('click', this._onClickGlobal, true);
            document.addEventListener('keydown', this._onKeydownGlobal);
        },
        _willDelete() {
            document.removeEventListener('click', this._onClickGlobal, true);
            document.removeEventListener('keydown', this._onKeydownGlobal);
        },
    },
    recordMethods: {
        /**
         * @param {Element} element
         * @returns {boolean}
         */
        hasElementInContent(element) {
            return Boolean(this.record && this.record.containsElement(element));
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeAttachmentDeleteConfirmView() {
            if (this.attachmentCardOwnerAsAttachmentDeleteConfirm) {
                return {};
            }
            if (this.attachmentImageOwnerAsAttachmentDeleteConfirm) {
                return {};
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeAttachmentViewer() {
            if (this.attachmentListOwnerAsAttachmentView) {
                return {};
            }
            return clear();
        },
        /**
         * @private
         * @returns {number}
         */
        _computeBackgroundOpacity() {
            if (this.attachmentViewer) {
                return 0.7;
            }
            return 0.5;
        },
        /**
         * @private
         * @returns {string}
         */
        _computeComponentClassName() {
            if (this.attachmentDeleteConfirmView) {
                return 'o_Dialog_componentMediumSize align-self-start mt-5';
            }
            if (this.deleteMessageConfirmView) {
                return 'o_Dialog_componentLargeSize align-self-start mt-5';
            }
            return '';
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeComponentName() {
            if (this.attachmentViewer) {
                return 'AttachmentViewer';
            }
            if (this.attachmentDeleteConfirmView) {
                return 'AttachmentDeleteConfirm';
            }
            if (this.deleteMessageConfirmView) {
                return 'DeleteMessageConfirm';
            }
            if (this.followerSubtypeList) {
                return 'FollowerSubtypeList';
            }
            if (this.linkPreviewDeleteConfirmView) {
                return 'LinkPreviewDeleteConfirmView';
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeDeleteMessageConfirmView() {
            return this.messageActionViewOwnerAsDeleteConfirm ? {} : clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeFollowerSubtypeList() {
            return this.followerOwnerAsSubtypeList ? {} : clear();
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsCloseable() {
            if (this.attachmentViewer) {
                /**
                 * Prevent closing the dialog when clicking on the mask when the user is
                 * currently dragging the image.
                 */
                return !this.attachmentViewer.isDragging;
            }
            return true;
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeLinkPreviewDeleteConfirmView() {
            return this.linkPreviewAsideViewOwnerAsLinkPreviewDeleteConfirm ? {} : clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeManager() {
            if (this.messaging.dialogManager) {
                return this.messaging.dialogManager;
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeRecord() {
            if (this.attachmentViewer) {
                return this.attachmentViewer;
            }
            if (this.attachmentDeleteConfirmView) {
                return this.attachmentDeleteConfirmView;
            }
            if (this.deleteMessageConfirmView) {
                return this.deleteMessageConfirmView;
            }
            if (this.linkPreviewDeleteConfirmView) {
                return this.linkPreviewDeleteConfirmView;
            }
            if (this.followerSubtypeList) {
                return this.followerSubtypeList;
            }
        },
        /**
         * @private
         * @returns {string}
         */
        _computeStyle() {
            return `background-color: rgba(0, 0, 0, ${this.backgroundOpacity});`;
        },
        /**
         * Closes the dialog when clicking outside.
         * Does not work with attachment viewer because it takes the whole space.
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onClickGlobal(ev) {
            if (this.hasElementInContent(ev.target)) {
                return;
            }
            if (!this.isCloseable) {
                return;
            }
            this.delete();
        },
        /**
         * @private
         * @param {KeyboardEvent} ev
         */
        _onKeydownGlobal(ev) {
            if (ev.key === 'Escape') {
                this.delete();
            }
        },
    },
    fields: {
        attachmentCardOwnerAsAttachmentDeleteConfirm: one('AttachmentCard', {
            identifying: true,
            inverse: 'attachmentDeleteConfirmDialog',
        }),
        attachmentDeleteConfirmView: one('AttachmentDeleteConfirmView', {
            compute: '_computeAttachmentDeleteConfirmView',
            inverse: 'dialogOwner',
            isCausal: true,
        }),
        attachmentImageOwnerAsAttachmentDeleteConfirm: one('AttachmentImage', {
            identifying: true,
            inverse: 'attachmentDeleteConfirmDialog',
        }),
        attachmentListOwnerAsAttachmentView: one('AttachmentList', {
            identifying: true,
            inverse: 'attachmentListViewDialog',
        }),
        attachmentViewer: one('AttachmentViewer', {
            compute: '_computeAttachmentViewer',
            inverse: 'dialogOwner',
            isCausal: true,
        }),
        backgroundOpacity: attr({
            compute: '_computeBackgroundOpacity',
        }),
        componentClassName: attr({
            compute: '_computeComponentClassName',
        }),
        componentName: attr({
            compute: '_computeComponentName',
            required: true,
        }),
        deleteMessageConfirmView: one('DeleteMessageConfirmView', {
            compute: '_computeDeleteMessageConfirmView',
            inverse: 'dialogOwner',
            isCausal: true,
        }),
        linkPreviewAsideViewOwnerAsLinkPreviewDeleteConfirm: one('LinkPreviewAsideView', {
            inverse: 'linkPreviewDeleteConfirmDialog',
            readonly: true,
        }),
        linkPreviewDeleteConfirmView: one('LinkPreviewDeleteConfirmView', {
            compute: '_computeLinkPreviewDeleteConfirmView',
            inverse: 'dialogOwner',
            isCausal: true,
        }),
        followerOwnerAsSubtypeList: one('Follower', {
            identifying: true,
            inverse: 'followerSubtypeListDialog',
        }),
        followerSubtypeList: one('FollowerSubtypeList', {
            compute: '_computeFollowerSubtypeList',
            inverse: 'dialogOwner',
            isCausal: true,
        }),
        isCloseable: attr({
            compute: '_computeIsCloseable',
            default: true,
        }),
        manager: one('DialogManager', {
            compute: '_computeManager',
            inverse: 'dialogs',
        }),
        messageActionViewOwnerAsDeleteConfirm: one('MessageActionView', {
            identifying: true,
            inverse: 'deleteConfirmDialog',
        }),
        /**
         * Content of dialog that is directly linked to a record that models
         * a UI component, such as AttachmentViewer. These records must be
         * created from @see `DialogManager:open()`.
         */
        record: one('Record', {
            compute: '_computeRecord',
            isCausal: true,
            required: true,
        }),
        style: attr({
            compute: '_computeStyle',
        }),
    },
});
