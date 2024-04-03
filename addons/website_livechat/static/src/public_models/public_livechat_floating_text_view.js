/** @odoo-module **/

import { PublicLivechatFloatingTextView } from '@website_livechat/legacy/widgets/public_livechat_floating_text_view/public_livechat_floating_text_view';

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'PublicLivechatFloatingTextView',
    lifecycleHooks: {
        _created() {
            const widget = new PublicLivechatFloatingTextView(this.livechatButtonViewOwner.widget, this.messaging);
            widget.appendTo(this.livechatButtonViewOwner.widget.$el);
            this.update({ widget });
        },
        _willDelete() {
            this.widget.destroy();
        },
    },
    fields: {
        livechatButtonViewOwner: one('LivechatButtonView', {
            identifying: true,
            inverse: 'floatingTextView',
        }),
        text: attr({
            related: 'livechatButtonViewOwner.buttonText',
        }),
        widget: attr(),
    },
});
