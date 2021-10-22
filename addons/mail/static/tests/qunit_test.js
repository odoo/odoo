/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one2one } from '@mail/model/model_field';

registerModel({
    name: 'mail.qunit_test',
    identifyingFields: [], // singleton acceptable (only one test at a time)
    fields: {
        composer: one2one('mail.composer', {
            isCausal: true,
        }),
        composerView: one2one('mail.composer_view', {
            inverse: 'qunitTest',
            isCausal: true,
        }),
        messageView: one2one('mail.message_view', {
            inverse: 'qunitTest',
            isCausal: true,
        }),
        threadViewer: one2one('mail.thread_viewer', {
            inverse: 'qunitTest',
            isCausal: true,
        }),
    },
});
