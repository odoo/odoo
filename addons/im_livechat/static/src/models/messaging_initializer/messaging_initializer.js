/** @odoo-module **/

import { registerInstancePatchModel } from '@mail/model/model_core';
import { create } from '@mail/model/model_field_command';
import { executeGracefully } from '@mail/utils/utils';

registerInstancePatchModel('mail.messaging_initializer', 'im_livechat/static/src/models/messaging_initializer/messaging_initializer.js', {

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * @override
     * @param {object} mailUserSettings
     * @param {boolean} mailUserSettings.is_discuss_sidebar_category_livechat_open
     */
    _initMailUserSettings({ is_discuss_sidebar_category_livechat_open }) {
        this.messaging.discuss.update({
            categoryLivechat: create({
                counterComputeMethod: 'unread',
                displayName: this.env._t("Livechat"),
                isServerOpen: is_discuss_sidebar_category_livechat_open,
                serverStateKey: 'is_discuss_sidebar_category_livechat_open',
                sortComputeMethod: 'last_action',
                supportedChannelTypes: ['livechat'],
            }),
        });
        this._super(...arguments);
    },

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
});
