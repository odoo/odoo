/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'FollowerSubtypeList',
    identifyingFields: ['dialogOwner'],
    recordMethods: {
        /**
         * Returns whether the given html element is inside this follower subtype list.
         *
         * @param {Element} element
         * @returns {boolean}
         */
        containsElement(element) {
            return Boolean(this.component && this.component.root.el && this.component.root.el.contains(element));
        },
    },
    fields: {
        /**
         * States the OWL component of this attachment viewer.
         */
        component: attr(),
        /**
         * States the dialog displaying this follower subtype list.
         */
        dialogOwner: one('Dialog', {
            inverse: 'followerSubtypeList',
            isCausal: true,
            readonly: true,
        }),
        follower: one('Follower', {
            related: 'dialogOwner.followerOwnerAsSubtypeList',
            required: true,
        }),
    },
});
