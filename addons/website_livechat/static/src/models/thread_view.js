/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerPatch({
    name: 'ThreadView',
    fields: {
        visitorBanner: one('VisitorBannerView', {
            compute() {
                if (this.thread && this.thread.visitor && this.threadViewer && this.threadViewer.discuss) {
                    return {};
                }
                return clear();
            },
            inverse: 'owner',
        }),
    },
});
