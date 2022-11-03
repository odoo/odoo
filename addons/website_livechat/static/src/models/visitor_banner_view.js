/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
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
