odoo.define('mail/static/src/models/channel_command/channel_command.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr } = require('mail/static/src/model/model_field.js');

function factory(dependencies) {

    class ChannelCommand extends dependencies['mail.model'] {}

    ChannelCommand.fields = {
        /**
         * Makes only sense for threads on model 'mail.channel'. Type of the channel (e.g. 'chat', 'channel' or 'groups')
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
