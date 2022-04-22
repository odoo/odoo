/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { replace } from '@mail/model/model_field_command';

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
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeThread() {
            return replace(this.composerViewOwner.composer.activeThread);
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
        thread: one('Thread', {
            compute: '_computeThread',
            required: true,
        }),
    },
});
