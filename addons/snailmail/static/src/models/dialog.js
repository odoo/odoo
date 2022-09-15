/** @odoo-module **/

import { addFields, patchFields } from '@mail/model/model_core';
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
        compute() {
            if (this.messageViewOwnerAsSnailmailError) {
                return {};
            }
            return clear();
        },
        inverse: 'dialogOwner',
    }),
});

patchFields('Dialog', {
    componentClassName: {
        compute() {
            if (this.snailmailErrorView) {
                return 'o_Dialog_componentMediumSize align-self-start mt-5';
            }
            return this._super();
        },
    },
    componentName: {
        compute() {
            if (this.snailmailErrorView) {
                return 'SnailmailError';
            }
            return this._super();
        },
    },
    record: {
        compute() {
            if (this.snailmailErrorView) {
                return this.snailmailErrorView;
            }
            return this._super();
        },
    },
});
