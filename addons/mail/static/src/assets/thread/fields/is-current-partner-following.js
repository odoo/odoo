/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isCurrentPartnerFollowing
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
        [Field/compute]
            @record
            .{Thread/followers}
            .{Collection/some}
                {Record/insert}
                    [Record/models]
                        Function
                    [Function/in]
                        item
                    [Function/out]
                        @item
                        .{Follower/partner}
                        .{&}
                            @follower
                            .{Follower/partner}
                            .{=}
                                {Env/currentPartner}
`;
