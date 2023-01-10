/** @odoo-module **/

import { registerFieldPatchModel, registerIdentifyingFieldsPatch } from '@mail/model/model_core';
import { one2one } from '@mail/model/model_field';

registerFieldPatchModel('mail.thread_viewer', 'qunit', {
    qunitTest: one2one('mail.qunit_test', {
        inverse: 'threadViewer',
        readonly: true,
    }),
});

registerIdentifyingFieldsPatch('mail.thread_viewer', 'qunit', identifyingFields => {
    identifyingFields[0].push('qunitTest');
});
