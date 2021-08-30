/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Mark this message as read, so that it no longer appears in current
        partner Inbox.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Message/markAsRead
        [Action/params]
            message
                [type]
                    Message
        [Action/behavior]
            {Record/doAsync}
                [0]
                    @message
                [1]
                    @env
                    .{Env/owlEnv}
                    .{Dict/get}
                        services
                    .{Dict/get}
                        rpc
                    .{Function/call}
                        [model]
                            mail.message
                        [method]
                            set_message_done
                        [args]
                            {Record/insert}
                                [Record/models]
                                    Collection
                                {Record/insert}
                                    [Record/models]
                                        Collection
                                    @message
                                    .{Message/id}
`;
