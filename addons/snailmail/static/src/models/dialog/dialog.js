/** @odoo-module **/

import { addFields, addRecordMethods, patchIdentifyingFields, patchRecordMethods } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@mail/models/dialog/dialog';

addFields('Dialog', {
    messageViewOwnerAsSnailmailError: one('MessageView', {
        readonly: true,
        inverse: 'snailmailErrorDialog',
    }),
    snailmailErrorView: one('SnailmailErrorView', {
        compute: '_computeSnailmailErrorView',
        isCausal: true,
        inverse: 'dialogOwner',
    }),
});

addRecordMethods('Dialog', {
    /**
     * @private
     * @returns {FieldCommand}
     */
    _computeSnailmailErrorView() {
        if (this.messageViewOwnerAsSnailmailError) {
            return insertAndReplace();
        }
        return clear();
    },
});

patchIdentifyingFields('Dialog', identifyingFields => {
    identifyingFields[0].push('messageViewOwnerAsSnailmailError');
});

patchRecordMethods('Dialog', {
    /**
     * @override
     */
    _computeComponentName() {
        if (this.snailmailErrorView) {
            return 'SnailmailError';
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeRecord() {
        if (this.snailmailErrorView) {
            return replace(this.snailmailErrorView);
        }
        return this._super();
    },
});
