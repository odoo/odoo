/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Toggle the starred status of the provided message.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Message/toggleStar
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
                            toggle_message_starred
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
