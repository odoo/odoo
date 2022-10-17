/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'ComposerSuggestedRecipientView',
    recordMethods: {
        onComponentUpdate() {
            if (this.checkboxRef.el && this.suggestedRecipientInfo) {
                this.checkboxRef.el.checked = this.suggestedRecipientInfo.isSelected;
            }
        },
    },
    fields: {
        /**
         * Reference of the checkbox. Useful to know whether it was checked or
         * not, to properly update the corresponding state in the record or to
         * prompt the user with the partner creation dialog.
         */
        checkboxRef: attr(),
        composerSuggestedRecipientListViewOwner: one('ComposerSuggestedRecipientListView', {
            identifying: true,
            inverse: 'composerSuggestedRecipientViews',
        }),
        suggestedRecipientInfo: one('SuggestedRecipientInfo', {
            identifying: true,
            inverse: 'composerSuggestedRecipientViews',
        }),
    },
});
