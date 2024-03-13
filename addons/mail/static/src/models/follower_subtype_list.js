/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'FollowerSubtypeList',
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
         * Called when clicking on apply button.
         *
         * @param {MouseEvent} ev
         */
        onClickApply(ev) {
            this.follower.updateSubtypes();
        },
        /**
         * Called when clicking on cancel button.
         *
         * @param {MouseEvent} ev
         */
        onClickCancel(ev) {
            this.follower.closeSubtypes();
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
            identifying: true,
            inverse: 'followerSubtypeList',
            isCausal: true,
        }),
        follower: one('Follower', {
            related: 'dialogOwner.followerOwnerAsSubtypeList',
            required: true,
        }),
        followerSubtypeViews: many('FollowerSubtypeView', {
            compute() {
                if (this.follower.subtypes.length === 0) {
                    return clear();
                }
                return this.follower.subtypes.map(subtype => ({ subtype }));
            },
            inverse: 'followerSubtypeListOwner',
            sort: [
                ['falsy-first', 'subtype.parentModel'],
                ['case-insensitive-asc', 'subtype.parentModel'],
                ['falsy-first', 'subtype.resModel'],
                ['case-insensitive-asc', 'subtype.resModel'],
                ['smaller-first', 'subtype.isInternal'],
                ['smaller-first', 'subtype.sequence'],
                ['smaller-first', 'subtype.id'],
            ],
        }),
    },
});
