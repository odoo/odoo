/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'MessageAuthorPrefixView',
    identifyingFields: [['threadNeedactionPreviewViewOwner', 'threadPreviewViewOwner']],
    fields: {
        threadNeedactionPreviewViewOwner: one('ThreadNeedactionPreviewView', {
            inverse: 'messageAuthorPrefixView',
            readonly: true,
        }),
        threadPreviewViewOwner: one('ThreadPreviewView', {
            inverse: 'messageAuthorPrefixView',
            readonly: true,
        }),
    },
});
