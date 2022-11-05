/** @odoo-module **/

import { clear, one, registerPatch } from '@mail/model';

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
