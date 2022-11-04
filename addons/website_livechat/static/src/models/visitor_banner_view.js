/** @odoo-module **/

import { one, registerModel } from '@mail/model';

registerModel({
    name: 'VisitorBannerView',
    template: 'website_livechat.VisitorBannerView',
    templateGetter: 'visitorBannerView',
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
