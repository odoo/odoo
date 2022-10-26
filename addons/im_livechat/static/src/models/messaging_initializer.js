/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { insert } from '@mail/model/model_field_command';

registerPatch({
    name: 'MessagingInitializer',
    recordMethods: {
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
    },
});
