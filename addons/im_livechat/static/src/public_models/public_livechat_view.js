/** @odoo-module **/

import PublicLivechatView from '@im_livechat/legacy/widgets/public_livechat_view/public_livechat_view';

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'PublicLivechatView',
    lifecycleHooks: {
        _created() {
            this.update({
                widget: new PublicLivechatView(this, this.global.Messaging, { displayMarkAsRead: false }),
            });
        },
        _willDelete() {
            this.widget.destroy();
        },
    },
    fields: {
        publicLivechatWindowOwner: one('PublicLivechatWindow', {
            identifying: true,
            inverse: 'publicLivechatView',
        }),
        widget: attr(),
    },
});
