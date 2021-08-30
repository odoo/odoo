/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Joins this thread. Only makes sense on channels.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/join
        [Action/params]
            record
                [type]
                    Thread
        [Action/behavior]
            @env
            .{Env/owlEnv}
            .{Dict/get}
                services
            .{Dict/get}
                rpc
            .{Function/call}
                [model]
                    mail.channel
                [method]
                    add_members
                [args]
                    {Record/insert}
                        [Record/models]
                            Collection
                        {Record/insert}
                            [Record/models]
                                Collection
                            @record
                            .{Thread/id}
                [kwargs]
                    [partner_ids]
                        {Env/currentPartner}
                        .{Partner/id}
`;
