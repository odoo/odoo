/** @odoo-module **/

import { clear, one, Patch } from '@mail/model';

Patch({
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
                    return 'SnailmailErrorView';
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
