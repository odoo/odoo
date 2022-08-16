/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'FollowerSubtypeView',
    recordMethods: {
        /**
         * Called when clicking on cancel button.
         *
         * @param {Event} ev
         */
        onChangeCheckbox(ev) {
            if (ev.target.checked) {
                this.follower.selectSubtype(this.subtype);
            } else {
                this.follower.unselectSubtype(this.subtype);
            }
        },
    },
    fields: {
        follower: one('Follower', {
            related: 'followerSubtypeListOwner.follower',
        }),
        followerSubtypeListOwner: one('FollowerSubtypeList', {
            identifying: true,
            inverse: 'followerSubtypeViews',
            readonly: true,
            required: true,
        }),
        subtype: one('FollowerSubtype', {
            identifying: true,
            inverse: 'followerSubtypeViews',
            readonly: true,
            required: true,
        }),
    },
});
