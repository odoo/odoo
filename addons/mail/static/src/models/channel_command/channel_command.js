/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { cleanSearchTerm } from '@mail/utils/utils';

function factory(dependencies) {

    class ChannelCommand extends dependencies['mail.model'] {

        /**
         * Fetches channel commands matching the given search term to extend the
         * JS knowledge and to update the suggestion list accordingly.
         *
         * In practice all channel commands are already fetched at init so this
         * method does nothing.
         *
         * @static
         * @param {string} searchTerm
         * @param {Object} [options={}]
         * @param {mail.thread} [options.thread] prioritize and/or restrict
         *  result in the context of given thread
         */
        static fetchSuggestions(searchTerm, { thread } = {}) {}

        /**
         * Returns a sort function to determine the order of display of channel
         * commands in the suggestion list.
         *
         * @static
         * @param {string} searchTerm
         * @param {Object} [options={}]
         * @param {mail.thread} [options.thread] prioritize result in the
         *  context of given thread
         * @returns {function}
         */
        static getSuggestionSortFunction(searchTerm, { thread } = {}) {
            const cleanedSearchTerm = cleanSearchTerm(searchTerm);
            return (a, b) => {
                const isATypeSpecific = a.channel_types;
                const isBTypeSpecific = b.channel_types;
                if (isATypeSpecific && !isBTypeSpecific) {
                    return -1;
                }
                if (!isATypeSpecific && isBTypeSpecific) {
                    return 1;
                }
                const cleanedAName = cleanSearchTerm(a.name || '');
                const cleanedBName = cleanSearchTerm(b.name || '');
                if (cleanedAName.startsWith(cleanedSearchTerm) && !cleanedBName.startsWith(cleanedSearchTerm)) {
                    return -1;
                }
                if (!cleanedAName.startsWith(cleanedSearchTerm) && cleanedBName.startsWith(cleanedSearchTerm)) {
                    return 1;
                }
                if (cleanedAName < cleanedBName) {
                    return -1;
                }
                if (cleanedAName > cleanedBName) {
                    return 1;
                }
                return a.id - b.id;
            };
        }

        /**
         * Returns channel commands that match the given search term.
         *
         * @static
         * @param {string} searchTerm
         * @param {Object} [options={}]
         * @param {mail.thread} [options.thread] prioritize and/or restrict
         *  result in the context of given thread
         * @returns {[mail.channel_command[], mail.channel_command[]]}
         */
        static searchSuggestions(searchTerm, { thread } = {}) {
            if (thread.model !== 'mail.channel') {
                // channel commands are channel specific
                return [[]];
            }
            const cleanedSearchTerm = cleanSearchTerm(searchTerm);
            return [this.messaging.commands.filter(command => {
                if (!cleanSearchTerm(command.name).includes(cleanedSearchTerm)) {
                    return false;
                }
                if (command.channel_types) {
                    return command.channel_types.includes(thread.channel_type);
                }
                return true;
            })];
        }

        /**
         * Executes this command on the given `mail.channel`.
         *
         * @static
         * @param {Object} param0
         * @param {mail.thread} param0.channel
         * @param {Object} [param0.body='']
         */
        async execute({ channel, body = '' }) {
            return this.env.services.rpc({
                model: 'mail.channel',
                method: this.methodName,
                args: [[channel.id]],
                kwargs: { body },
            });
        }

        /**
         * Returns the text that identifies this channel command in a mention.
         *
         * @returns {string}
         */
        getMentionText() {
            return this.name;
        }

    }

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
        help: attr({
            required: true,
        }),
        /**
         * Name of the method of `mail.channel` to call on the server when
         * executing this command.
         */
        methodName: attr({
            required: true,
        }),
        /**
         *  The keyword to use a specific command.
         */
        name: attr({
            readonly: true,
            required: true,
        }),
    };
    ChannelCommand.identifyingFields = ['name'];
    ChannelCommand.modelName = 'mail.channel_command';

    return ChannelCommand;
}

registerNewModel('mail.channel_command', factory);
