/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';

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
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeFollowerSubtypeViews() {
            if (this.follower.subtypes.length === 0) {
                return clear();
            }
            return insertAndReplace(this.follower.subtypes.map(subtype => ({ subtype: replace(subtype) })));
        },
        /**
         * @private
         * @returns {Array}
         */
        _sortFollowerSubtypeViews() {
            return [
                ['smaller-first', 'subtype.id'],
            ];
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
        followerSubtypeViews: many('FollowerSubtypeView', {
            compute: '_computeFollowerSubtypeViews',
            inverse: 'followerSubtypeListOwner',
            isCausal: true,
            sort: '_sortFollowerSubtypeViews',
        }),
    },
});
