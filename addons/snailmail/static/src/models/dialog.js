/** @odoo-module **/

import { addFields, addRecordMethods, patchRecordMethods } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@mail/models/dialog';

addFields('Dialog', {
    messageViewOwnerAsSnailmailError: one('MessageView', {
        identifying: true,
        inverse: 'snailmailErrorDialog',
    }),
    snailmailErrorView: one('SnailmailErrorView', {
        compute: '_computeSnailmailErrorView',
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
            return {};
        }
        return clear();
    },
});

patchRecordMethods('Dialog', {
    /**
     * @private
     * @returns {string}
     */
    _computeComponentClassName() {
        if (this.snailmailErrorView) {
            return 'o_Dialog_componentMediumSize align-self-start mt-5';
        }
        return this._super();
    },
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
            return this.snailmailErrorView;
        }
        return this._super();
    },
});
