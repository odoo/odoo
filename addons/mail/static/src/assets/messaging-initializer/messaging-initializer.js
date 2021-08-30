/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            MessagingInitializer
        [Model/id]
            MessagingInitializer/messaging
        [Model/actions]
            MessagingInitializer/_init
            MessagingInitializer/_initCannedResponses
            MessagingInitializer/_initChannels
            MessagingInitializer/_initCommands
            MessagingInitializer/_initMailboxes
            MessagingInitializer/_initMailFailures
            MessagingInitializer/_initPartners
            MessagingInitializer/_initResUsersSettings
            MessagingInitializer/_loadMessageFailures
            MessagingInitializer/start
            MessagingInitializer/stop
`;
