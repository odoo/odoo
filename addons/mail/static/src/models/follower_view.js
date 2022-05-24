/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'FollowerView',
    identifyingFields: ['followerListMenuViewOwner', 'follower'],
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            this.followerListMenuViewOwner.hide();
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickDetails(ev) {
            ev.preventDefault();
            ev.stopPropagation();
            this.follower.openProfile();
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickEdit(ev) {
            ev.preventDefault();
            this.follower.showSubtypes();
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickRemove(ev) {
            this.follower.remove();
        },
    },
    fields: {
        follower: one('Follower', {
            inverse: 'followerViews',
            readonly: true,
            required: true,
        }),
        followerListMenuViewOwner: one('FollowerListMenuView', {
            inverse: 'followerViews',
            readonly: true,
            required: true,
        }),
    },
});
