/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Mark all messages of current user with given domain as read.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Message/markAllAsRead
        [Action/params]
            domain
                [type]
                    Domain
        [Action/behavior]
            @env
            .{Env/owlEnv}
            .{Dict/get}
                services
            .{Dict/get}
                rpc
            .{Function/call}
                [0]
                    [model]
                        mail.message
                    [method]
                        mark_all_as_read
                    [kwargs]
                        [domain]
                            @domain
                [1]
                    [shadow]
                        true
`;
