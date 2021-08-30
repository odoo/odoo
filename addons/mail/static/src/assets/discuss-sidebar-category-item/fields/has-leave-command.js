/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Boolean determines whether the item has a "leave" command
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasLeaveCommand
        [Field/model]
            DiscussSidebarCategoryItem
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            {Record/insert}
                [Record/models]
                    Collection
                channel
                group
            .{Collection/includes}
                @record
                .{DiscussSidebarCategoryItem/channelType}
            .{&}
                @record
                .{DiscussSidebarCategoryItem/channel}
                .{Thread/messageNeedactionCounter}
                .{isFalsy}
            .{&}
                @record
                .{DiscussSidebarCategoryItem/channel}
                .{Thread/isGroupBasedSubscription}
`;
