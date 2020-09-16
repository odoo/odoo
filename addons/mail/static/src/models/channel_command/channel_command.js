odoo.define('mail/static/src/models/channel_command/channel_command.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr } = require('mail/static/src/model/model_field_utils.js');

function factory(dependencies) {

    class ChannelCommand extends dependencies['mail.model'] {}

    ChannelCommand.fields = {
        /**
         * FIXME use this value task-2343850
         */
        __mfield_channel_types: attr(),
        /**
         *  The command that will be executed.
         */
        __mfield_help: attr(),
        /**
         *  The keyword to use a specific command.
         */
        __mfield_name: attr(),
    };

    ChannelCommand.modelName = 'mail.channel_command';

    return ChannelCommand;
}

registerNewModel('mail.channel_command', factory);

});
