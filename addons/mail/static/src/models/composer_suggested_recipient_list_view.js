/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'ComposerSuggestedRecipientListView',
    identifyingFields: ['composerViewOwner'],
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClickShowLess(ev) {
            if (!this.exists()) {
                return;
            }
            this.update({ hasShowMoreButton: false });
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickShowMore(ev) {
            if (!this.exists()) {
                return;
            }
            this.update({ hasShowMoreButton: true });
        },
    },
    fields: {
        composerViewOwner: one('ComposerView', {
            inverse: 'composerSuggestedRecipientListView',
            readonly: true,
            required: true,
        }),
        hasShowMoreButton: attr({
            default: false,
        }),
    },
});
