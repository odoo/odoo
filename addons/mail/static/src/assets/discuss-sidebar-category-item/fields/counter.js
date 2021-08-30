/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Amount of unread/action-needed messages
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            counter
        [Field/model]
            DiscussSidebarCategoryItem
        [Field/type]
            attr
        [Field/target]
            Integer
        [Field/compute]
            {switch}
                @record
                .{DiscussSidebarCategoryItem/channelType}
            .{case}
                [channel]
                    @record
                    .{DiscussSidebarCategoryItem/channel}
                    .{Thread/messageNeedactionCounter}
                [group]
                    @record
                    .{DiscussSidebarCategoryItem/channel}
                    .{Thread/localMessageUnreadCounter}
                [chat]
                    @record
                    .{DiscussSidebarCategoryItem/channel}
                    .{Thread/localMessageUnreadCounter}
`;
