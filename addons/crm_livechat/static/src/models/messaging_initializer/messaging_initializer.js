/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
import { insert } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@mail/models/messaging_initializer/messaging_initializer';

patchRecordMethods('MessagingInitializer', {
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
});
