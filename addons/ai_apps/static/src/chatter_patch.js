import { Chatter } from "@mail/chatter/web_portal/chatter";

import { patch } from "@web/core/utils/patch";

/**
 * @type {import("@mail/chatter/web_portal/chatter").Chatter }
 * @typedef {Object} Props
 * @property {function} [close]
 */
patch(Chatter.prototype, {
    setup() {
        super.setup();
    },
    async onClickAIChatterButton() {
        // create the discuss channel used for talking with the ai
        const ai_channel_id = await this.orm.call(
            'discuss.channel',
            'create_ai_composer_channel',
            [ 
                'chatter_ai_button',
                this.props.record.data.name,
                this.props.record.resModel,
                this.props.record.resId,
            ], 
        );
        // create and open the thread for the discuss channel
        const thread = await this.store.Thread.getOrFetch({
            model: "discuss.channel",
            id: Number(ai_channel_id), 
        });
        thread.open({ 
            focus: true, 
            specialActions: {
                'sendMessage': (content) => {
                    console.log("Send message");
                },
                'logNote': (content) => {
                    console.log("Log Note");
                }
            },
            chatCaller: this.props.record.id,
            composerText: 'Summarize the chatter conversation',
        });
        return;
    },
});
