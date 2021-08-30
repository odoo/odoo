/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            correspondent
        [Field/model]
            Thread
        [Field/type]
            one
        [Field/target]
            Partner
        [Field/compute]
            {if}
                @record
                .{Thread/channelType}
                .{=}
                    channel
            .{then}
                {Record/empty}
                {break}
            :correspondents
                @record
                .{Thread/members}
                .{Collection/filter}
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            item
                        [Function/out]
                            @item
                            .{!=}
                                {Env/currentPartner}
            {if}
                @correspondents
                .{Collection/length}
                .{=}
                    1
            .{then}
                {Dev/comment}
                    2 members chat
                @correspondents
                .{Collection/first}
            .{elif}
                @record
                .{Thread/members}
                .{Collection/length}
                .{=}
                    1
            .{then}
                {Dev/comment}
                    chat with oneself
                @record
                .{Thread/members}
                .{Collection/first}
            .{else}
                {Record/empty}
`;
