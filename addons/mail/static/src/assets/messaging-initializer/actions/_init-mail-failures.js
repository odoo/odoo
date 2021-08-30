/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingInitializer/_initMailFailures
        [Action/params]
            messagingInitializer
                [type]
                    MessagingInitializer
            mailFailuresData
                [type]
                    Object
        [Action/behavior]
            {Utils/executeGracefully}
                @mailFailuresData
                .{Collection/map}
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            item
                        [Function/out]
                            :message
                                {Record/insert}
                                    [Record/models]
                                        Message
                                    {Message/convertData}
                                        @item
                            {Dev/comment}
                                implicit: failures are sent by the server
                                at initialization only if the current
                                partner is author of the message
                            {if}
                                @message
                                .{Message/author}
                                .{isFalsy}
                                .{&}
                                    {Env/currentPartner}
                            .{then}
                                {Record/update}
                                    [0]
                                        @message
                                    [1]
                                        [Message/author]
                                            {Env/currentPartner}
`;
