/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
import { markEventHandled } from '@mail/utils/utils';

registerModel({
    name: 'MessageActionView',
    recordMethods: {
        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            switch (this.messageAction.messageActionListOwner) {
                case this.messageAction.messageActionListOwnerAsDelete:
                    this.update({ deleteConfirmDialog: {} });
                    break;
                case this.messageAction.messageActionListOwnerAsEdit:
                    this.messageAction.messageActionListOwner.messageView.startEditing();
                    break;
                case this.messageAction.messageActionListOwnerAsMarkAsRead:
                    this.messageAction.messageActionListOwner.message.markAsRead();
                    break;
                case this.messageAction.messageActionListOwnerAsReaction:
                    if (!this.reactionPopoverView) {
                        this.update({ reactionPopoverView: {} });
                    } else {
                        this.update({ reactionPopoverView: clear() });
                    }
                    break;
                case this.messageAction.messageActionListOwnerAsReplyTo:
                    markEventHandled(ev, 'MessageActionList.replyTo');
                    this.messageAction.messageActionListOwner.messageView.replyTo();
                    break;
                case this.messageAction.messageActionListOwnerAsToggleCompact:
                    this.messageAction.messageActionListOwner.update({ isCompact: !this.messageAction.messageActionListOwner.isCompact });
                    break;
                case this.messageAction.messageActionListOwnerAsToggleStar:
                    this.messageAction.messageActionListOwner.message.toggleStar();
                    break;
            }
        },
        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClickReaction(ev) {
            this.messageAction.messageActionListOwner.message.addReaction(ev.currentTarget.dataset.unicode);
            this.update({ reactionPopoverView: clear() });
        },
        /**
         * @private
         * @returns {boolean|FieldCommand}
         */
        _computeAriaPressedState() {
            if (this.messageAction.messageActionListOwnerAsToggleStar) {
                return this.messageAction.messageActionListOwnerAsToggleStar.message.isStarred;
            }
            return clear();
        },
        /**
         * @private
         * @returns {string}
         */
        _computeClassNames() {
            const classNames = [];
            classNames.push(this.paddingClassNames);
            switch (this.messageAction.messageActionListOwner) {
                case this.messageAction.messageActionListOwnerAsDelete:
                    classNames.push('fa fa-lg fa-trash o_MessageActionView_actionDelete');
                    break;
                case this.messageAction.messageActionListOwnerAsEdit:
                    classNames.push('fa fa-lg fa-pencil o_MessageActionView_actionEdit');
                    break;
                case this.messageAction.messageActionListOwnerAsMarkAsRead:
                    classNames.push('fa fa-lg fa-check o_MessageActionView_actionMarkAsRead');
                    break;
                case this.messageAction.messageActionListOwnerAsReaction:
                    classNames.push('fa fa-lg fa-smile-o o_MessageActionView_actionReaction');
                    break;
                case this.messageAction.messageActionListOwnerAsReplyTo:
                    classNames.push('fa fa-lg fa-reply o_MessageActionView_actionReplyTo');
                    break;
                case this.messageAction.messageActionListOwnerAsToggleCompact:
                    classNames.push('fa fa-lg fa-ellipsis-h o_MessageAction_actionToggleCompact');
                    break;
                case this.messageAction.messageActionListOwnerAsToggleStar:
                    classNames.push('fa fa-lg o_MessageActionView_actionToggleStar');
                    if (this.messageAction.messageActionListOwner.message.isStarred) {
                        classNames.push(`fa-star o_MessageActionView_actionToggleStar_active`);
                    } else {
                        classNames.push('fa-star-o');
                    }
                    break;
            }
            return classNames.join(' ');
        },
        /**
         * @private
         * @returns {string}
         */
        _computePaddingClassNames() {
            const isDeviceSmall = this.messaging.device.isSmall;
            const paddingClassNames = [];
            if (this.messageAction.messageActionListOwner.firstActionView === this) {
                paddingClassNames.push(isDeviceSmall ? 'ps-3' : 'ps-2');
            } else {
                paddingClassNames.push(isDeviceSmall ? 'ps-2' : 'ps-1');
            }
            if (this.messageAction.messageActionListOwner.lastActionView === this) {
                paddingClassNames.push(isDeviceSmall ? 'pe-3' : 'pe-2');
            } else {
                paddingClassNames.push(isDeviceSmall ? 'pe-2' : 'pe-1');
            }
            paddingClassNames.push(isDeviceSmall ? 'py-3' : 'py-2');
            return paddingClassNames.join(' ');
        },
        /**
         * @private
         * @returns {integer|FieldCommand}
         */
        _computeTabindex() {
            if (this.messageAction.messageActionListOwnerAsReaction) {
                return clear();
            }
            return 0;
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeTitle() {
            switch (this.messageAction.messageActionListOwner) {
                case this.messageAction.messageActionListOwnerAsDelete:
                    return this.env._t("Delete");
                case this.messageAction.messageActionListOwnerAsEdit:
                    return this.env._t("Edit");
                case this.messageAction.messageActionListOwnerAsMarkAsRead:
                    return this.env._t("Mark as Read");
                case this.messageAction.messageActionListOwnerAsReaction:
                    return this.env._t("Add a Reaction");
                case this.messageAction.messageActionListOwnerAsReplyTo:
                    return this.env._t("Reply");
                case this.messageAction.messageActionListOwnerAsToggleCompact:
                    return this.env._t("Compact");
                case this.messageAction.messageActionListOwnerAsToggleStar:
                    return this.env._t("Mark as Todo");
                default:
                    return clear();
            }
        },
    },
    fields: {
        /**
         * States the reference to the action in the component.
         */
        actionRef: attr(),
        actionViewCounterContribution: attr({
            default: 1,
            readonly: true,
        }),
        ariaPressedState: attr({
            compute: '_computeAriaPressedState',
        }),
        classNames: attr({
            default: '',
            compute: '_computeClassNames',
        }),
        deleteConfirmDialog: one('Dialog', {
            inverse: 'messageActionViewOwnerAsDeleteConfirm',
            isCausal: true,
        }),
        messageAction: one('MessageAction', {
            identifying: true,
            inverse: 'messageActionView',
        }),
        paddingClassNames: attr({
            compute: '_computePaddingClassNames',
            default: '',
        }),
        reactionPopoverView: one('PopoverView', {
            inverse: 'messageActionViewOwnerAsReaction',
            isCausal: true,
        }),
        tabindex: attr({
            compute: '_computeTabindex',
        }),
        title: attr({
            default: '',
            compute: '_computeTitle',
        }),
    },
});
