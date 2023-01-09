/** @odoo-module **/

import { insert, Patch } from '@mail/model';

Patch({
    name: 'MessagingInitializer',
    recordMethods: {
        /**
         * @override
         */
        _initCommands() {
            this._super();
            this.messaging.update({
                commands: insert({
                    help: this.env._t("Create a new lead (/lead lead title)"),
                    methodName: 'execute_command_lead',
                    name: "lead",
                }),
            });
        },
    },
});
