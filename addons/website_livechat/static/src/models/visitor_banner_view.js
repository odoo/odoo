/** @odoo-module **/

import { one, Model } from '@mail/model';

Model({
    name: 'VisitorBannerView',
    template: 'website_livechat.VisitorBannerView',
    fields: {
        owner: one('ThreadView', {
            identifying: true,
            inverse: 'visitorBanner',
        }),
        visitor: one('Visitor', {
            compute() {
                return this.owner.thread.visitor;
            },
            required: true,
        }),
    },
});
