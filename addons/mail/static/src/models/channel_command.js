/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';
import { cleanSearchTerm } from '@mail/utils/utils';

registerModel({
    name: 'ChannelCommand',
    modelMethods: {
        /**
         * Fetches channel commands matching the given search term to extend the
         * JS knowledge and to update the suggestion list accordingly.
         *
         * In practice all channel commands are already fetched at init so this
         * method does nothing.
         *
         * @param {string} searchTerm
         * @param {Object} [options={}]
         * @param {Thread} [options.thread] prioritize and/or restrict
         *  result in the context of given thread
         */
        fetchSuggestions(searchTerm, { thread } = {}) {},
        /**
         * Returns a sort function to determine the order of display of channel
         * commands in the suggestion list.
         *
         * @param {string} searchTerm
         * @param {Object} [options={}]
         * @param {Thread} [options.thread] prioritize result in the
         *  context of given thread
         * @returns {function}
         */
        getSuggestionSortFunction(searchTerm, { thread } = {}) {
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
        },
        /**
         * Returns channel commands that match the given search term.
         *
         * @param {string} searchTerm
         * @param {Object} [options={}]
         * @param {Thread} [options.thread] prioritize and/or restrict
         *  result in the context of given thread
         * @returns {[ChannelCommand[], ChannelCommand[]]}
         */
        searchSuggestions(searchTerm, { thread } = {}) {
            if (!thread.channel) {
                // channel commands are channel specific
                return [[]];
            }
            const cleanedSearchTerm = cleanSearchTerm(searchTerm);
            return [this.messaging.commands.filter(command => {
                if (!cleanSearchTerm(command.name).includes(cleanedSearchTerm)) {
                    return false;
                }
                if (command.channel_types) {
                    return command.channel_types.includes(thread.channel.channel_type);
                }
                return true;
            })];
        },
    },
    recordMethods: {
        /**
         * Executes this command on the given `mail.channel`.
         *
         * @param {Object} param0
         * @param {Thread} param0.channel
         * @param {Object} [param0.body='']
         */
        async execute({ channel, body = '' }) {
            return this.messaging.rpc({
                model: 'mail.channel',
                method: this.methodName,
                args: [[channel.id]],
                kwargs: { body },
            });
        },
    },
    fields: {
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
            identifying: true,
        }),
        suggestable: one('ComposerSuggestable', {
            default: insertAndReplace(),
            inverse: 'channelCommand',
            isCausal: true,
            readonly: true,
            required: true,
        }),
    },
});
