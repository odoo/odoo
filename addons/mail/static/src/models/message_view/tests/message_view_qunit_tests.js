/** @odoo-module **/

import { registerFieldPatchModel, registerIdentifyingFieldsPatch } from '@mail/model/model_core';
import { one2one } from '@mail/model/model_field';

registerFieldPatchModel('mail.message_view', 'qunit', {
    qunitTest: one2one('mail.qunit_test', {
        inverse: 'messageView',
        readonly: true,
    }),
});

registerIdentifyingFieldsPatch('mail.message_view', 'qunit', identifyingFields => {
    identifyingFields[0].push('qunitTest');
});
