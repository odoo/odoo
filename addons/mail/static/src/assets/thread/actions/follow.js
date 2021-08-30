/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Add current user to provided thread's followers.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/follow
        [Action/params]
            record
                [type]
                    Thread
        [Action/behavior]
            {Record/doAsync}
                [0]
                    @record
                [1]
                    @env
                    .{Env/owlEnv}
                    .{Dict/get}
                        services
                    .{Dict/get}
                        rpc
                    .{Function/call}
                        [model]
                            @record
                            .{Thread/model}
                        [method]
                            message_subscribe
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
            {Thread/fetchData}
                [0]
                    @record
                [1]
                    followers
                    suggestedRecipients
`;
