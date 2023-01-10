/** @odoo-module **/

import { registerFieldPatchModel, registerIdentifyingFieldsPatch } from '@mail/model/model_core';
import { one2one } from '@mail/model/model_field';

registerFieldPatchModel('mail.discuss_sidebar_category', 'im_livechat', {
    discussAsLivechat: one2one('mail.discuss', {
        inverse: 'categoryLivechat',
        readonly: true,
    }),
});

registerIdentifyingFieldsPatch('mail.discuss_sidebar_category', 'im_livechat', identifyingFields => {
    identifyingFields[0].push('discussAsLivechat');
});
