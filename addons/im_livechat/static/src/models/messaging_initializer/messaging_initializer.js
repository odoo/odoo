/** @odoo-module **/

import { registerInstancePatchModel } from '@mail/model/model_core';
import { insert, insertAndReplace } from '@mail/model/model_field_command';

registerInstancePatchModel('mail.messaging_initializer', 'im_livechat/static/src/models/messaging_initializer/messaging_initializer.js', {
    /**
     * @override
     * @param {Object} resUsersSettings
     * @param {boolean} resUsersSettings.is_discuss_sidebar_category_livechat_open
     */
    _initResUsersSettings({ is_discuss_sidebar_category_livechat_open }) {
        this.messaging.discuss.update({
            categoryLivechat: insertAndReplace({
                isServerOpen: is_discuss_sidebar_category_livechat_open,
                name: this.env._t("Livechat"),
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
