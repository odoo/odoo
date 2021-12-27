/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many2one, one2one } from '@mail/model/model_field';

registerModel({
    name: 'FollowerSubtypeList',
    identifyingFields: ['follower'],
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
        dialog: one2one('Dialog', {
            inverse: 'followerSubtypeList',
            isCausal: true,
            readonly: true,
        }),
        follower: many2one('Follower', {
            inverse: 'subtypeList',
            readonly: true,
            required: true,
        }),
    },
});
