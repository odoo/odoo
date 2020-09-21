odoo.define('mail/static/src/models/channel_command/channel_command.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr } = require('mail/static/src/model/model_field.js');

function factory(dependencies) {

    class ChannelCommand extends dependencies['mail.model'] {}

    ChannelCommand.fields = {
        /**
         * FIXME use this value task-2343850
         */
        channel_types: attr(),
        /**
         *  The command that will be executed.
         */
        help: attr(),
        /**
         *  The keyword to use a specific command.
         */
        name: attr(),
    };

    ChannelCommand.modelName = 'mail.channel_command';

    return ChannelCommand;
}

registerNewModel('mail.channel_command', factory);

});
