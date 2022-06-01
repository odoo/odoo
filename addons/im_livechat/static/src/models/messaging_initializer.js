/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
import { insert, insertAndReplace } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@mail/models/messaging_initializer';

patchRecordMethods('MessagingInitializer', {
    /**
     * @override
     */
    _initResUsersSettings(...args) {
        this._super(...args);
        this.messaging.discuss.update({
            categoryLivechat: insertAndReplace({
                serverStateKey: 'is_discuss_sidebar_category_livechat_open',
            }),
        });
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
