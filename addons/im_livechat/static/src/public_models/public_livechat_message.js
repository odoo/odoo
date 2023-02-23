/** @odoo-module **/

import { attr, clear, Model } from "@mail/model";

import PublicLivechatMessage from "@im_livechat/legacy/models/public_livechat_message";

Model({
    name: "PublicLivechatMessage",
    lifecycleHooks: {
        _created() {
            this.update({
                widget: new PublicLivechatMessage(
                    this.messaging.publicLivechatGlobal.livechatButtonView.widget,
                    this.messaging,
                    this.data
                ),
            });
        },
        _willDelete() {
            this.widget.destroy();
        },
    },
    fields: {
        authorId: attr({
            compute() {
                if (this.data.author && this.data.author.id) {
                    return this.data.author.id;
                }
                return clear();
            },
        }),
        data: attr(),
        id: attr({
            identifying: true,
        }),
        widget: attr(),
    },
});
