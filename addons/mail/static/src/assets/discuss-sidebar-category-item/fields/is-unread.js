/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Boolean determines whether the item has any unread messages.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isUnread
        [Field/model]
            DiscussSidebarCategoryItem
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            {if}
                @record
                .{DiscussSidebarCategoryItem/channel}
                .{isFalsy}
            .{then}
                {Record/empty}
            .{else}
                @record
                .{DiscussSidebarCategoryItem/channel}
                .{Thread/localMessageUnreadCounter}
                .{>}
                    0
`;
