/** @odoo-module **/

import { registerInstancePatchModel } from '@mail/model/model_core';
import { executeGracefully } from '@mail/utils/utils';
import { insert } from '@mail/model/model_field_command';

registerInstancePatchModel('mail.messaging_initializer', 'im_livechat/static/src/models/messaging_initializer/messaging_initializer.js', {

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * @override
     * @param {Object[]} [param0.channel_livechat=[]]
     */
    async _initChannels(initMessagingData) {
        await this.async(() => this._super(initMessagingData));
        const { channel_livechat = [] } = initMessagingData;
        return executeGracefully(channel_livechat.map(data => () => {
            const channel = this.env.models['mail.thread'].insert(
                this.env.models['mail.thread'].convertData(data),
            );
            // flux specific: channels received at init have to be
            // considered pinned. task-2284357
            if (!channel.isPinned) {
                channel.pin();
            }
        }));
    },
    /**
     * @override
     */
    _initCommands() {
        this._super();
        this.messaging.update({
            commands: insert({
                channel_types: ['livechat'],
                help: this.env._t("See 15 last visited pages"),
                methodName: 'execute_command_history',
                name: "history",
            }),
        });
    },
});
