/** @odoo-module **/

import { addFields, patchFields } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/thread_viewer';

addFields('ThreadViewer', {
    discussPublicView: one('DiscussPublicView', {
        identifying: true,
        inverse: 'threadViewer',
    }),
});

patchFields('ThreadViewer', {
    threadView_hasComposerThreadTyping: {
        compute() {
            if (this.discussPublicView) {
                return true;
            }
            return this._super();
        },
    },
});
