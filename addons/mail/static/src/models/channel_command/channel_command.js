odoo.define('mail/static/src/models/channel_command/channel_command.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr } = require('mail/static/src/model/model_field.js');

function factory(dependencies) {

    class ChannelCommand extends dependencies['mail.model'] {}

    ChannelCommand.fields = {
        /**
         * Determines on which channel types `this` is available.
         * Type of the channel (e.g. 'chat', 'channel' or 'groups')
         * This field should contain an array when filtering is desired.
         * Otherwise, it should be undefined when all types are allowed.
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
