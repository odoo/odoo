/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
import { insert, insertAndReplace } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@mail/models/messaging_initializer';

patchRecordMethods('MessagingInitializer', {
    /**
     * @override
     */
    async performInitRpc() {
        if (this.messaging.isInPublicLivechat) {
            return {};
        } else {
            return this._super();
        }
    },
    /**
     * @override
     * @param {Object} resUsersSettings
     * @param {boolean} resUsersSettings.is_discuss_sidebar_category_livechat_open
     */
    _initResUsersSettings({ is_discuss_sidebar_category_livechat_open }) {
        this.messaging.discuss.update({
            categoryLivechat: insertAndReplace({
                isServerOpen: is_discuss_sidebar_category_livechat_open,
                serverStateKey: 'is_discuss_sidebar_category_livechat_open',
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
