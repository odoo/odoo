/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            FieldAddon
        [FieldAddon/field]
            DiscussSidebarCategoryItem/avatarUrl
        [FieldAddon/feature]
            im_livechat
        [FieldAddon/compute]
            {if}
                @record
                .{DiscussSidebarCategoryItem/channelType}
                .{=}
                    livechat
                .{&}
                    @record
                    .{DiscussSidebarCategoryItem/channel}
                    .{Thread/correspondent}
                .{&}
                    @record
                    .{DiscussSidebarCategoryItem/channel}
                    .{Thread/correspondent}
                    .{Partner/id}
                    .{>}
                        0
            .{then}
                @record
                .{DiscussSidebarCategoryItem/channel}
                .{Thread/correspondent}
                .{Partner/avatarUrl}
            .{else}
                @original
`;
