/** @odoo-module **/

import { PublicLivechatFloatingTextView } from '@website_livechat/legacy/widgets/public_livechat_floating_text_view/public_livechat_floating_text_view';

import { attr, one, Model } from '@mail/legacy/model';

Model({
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
