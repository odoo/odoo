/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Unfollow current partner from this thread.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/unfollow
        [Action/params]
            thread
                [type]
                    Thread
        [Action/behavior]
            :currentPartnerFollower
                @thread
                .{Thread/followers}
                .{Collection/find}
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            item
                        [Function/out]
                            @item
                            .{Follower/partner}
                            .{=}
                                {Env/currentPartner}
            {Record/doAsync}
                [0]
                    @thread
                [1]
                    {Follower/remove}
                        @currentPartnerFollower
`;
