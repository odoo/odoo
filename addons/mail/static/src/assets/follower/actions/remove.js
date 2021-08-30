/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Remove this follower from its related thread.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Follower/remove
        [Action/params]
            follower
                [type]
                    Follower
        [Action/behavior]
            {Record/doAsync}
                [0]
                    @follower
                [1]
                    @env
                    .{Env/owlEnv}
                    .{Dict/get}
                        services
                    .{Dict/get}
                        rpc
                    .{Function/call}
                        [model]
                            @follower
                            .{Follower/followedThread}
                            .{Thread/model}
                        [method]
                            message_unsubscribe
                        [args]
                            {Record/insert}
                                [Record/models]
                                    Collection
                                [0]
                                    @follower
                                    .{Follower/followedThread}
                                    .{Thread/id}
                                [1]
                                    @follower
                                    .{Follower/partner}
                                    .{Partner/id}
            {Record/delete}
                @follower
            {Thread/fetchData}
                [0]
                    @follower
                    .{Follower/followedThread}
                [1]
                    suggestedRecipients
`;
