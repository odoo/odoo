/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles click on the "load more members" button.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/onClickLoadMoreMembers
        [Action/params]
            record
                [type]
                    Thread
        [Action/behavior]
            :members
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
                        load_more_members
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
                        [known_member_ids]
                            @record
                            .{Thread/members}
                            .{Collection/map}
                                {Record/insert}
                                    [Record/models]
                                        Function
                                    [Function/in]
                                        item
                                    [Function/out]
                                        @item
                                        .{Partner/id}
            {Record/update}
                [0]
                    @record
                [1]
                    [Thread/members]
                        @members
`;
