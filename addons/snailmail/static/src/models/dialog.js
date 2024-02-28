/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerPatch({
    name: 'Dialog',
    fields: {
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
        messageViewOwnerAsSnailmailError: one('MessageView', {
            identifying: true,
            inverse: 'snailmailErrorDialog',
        }),
        record: {
            compute() {
                if (this.snailmailErrorView) {
                    return this.snailmailErrorView;
                }
                return this._super();
            },
        },
        snailmailErrorView: one('SnailmailErrorView', {
            compute() {
                if (this.messageViewOwnerAsSnailmailError) {
                    return {};
                }
                return clear();
            },
            inverse: 'dialogOwner',
        }),
    },
});
