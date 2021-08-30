/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ActionAddon
        [ActionAddon/action]
            MessagingInitializer/_initCommands
        [ActionAddon/feature]
            im_livechat
        [ActionAddon/params]
            messagingInitializer
        [ActionAddon/behavior]
            @original
            {Record/update}
                [0]
                    @env
                [1]
                    [Env/commands]
                        {Field/add}
                            {Record/insert}
                                [Record/models]
                                    ChannelCommand
                                [ChannelCommand/channelTypes]
                                    livechat
                                [ChannelCommand/help]
                                    {Locale/text}
                                        See 15 last visited pages
                                [ChannelCommand/methodName]
                                    execute_command_history
                                [ChannelCommand/name]
                                    history
`;
