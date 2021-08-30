/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Image URL for the related channel thread.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            avatarUrl
        [Field/model]
            DiscussSidebarCategoryItem
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {switch}
                @record
                .{DiscussSidebarCategoryItem/channelType}
            .{case}
                [channel]
                    /web/image/mail.channel/
                    .{+}
                        @record
                        .{DiscussSidebarCategoryItem/channel}
                        .{Thread/id}
                    .{+}
                        /image_128
                    .{+}
                        ?unique=
                    .{+}
                        @record
                        .{ThreadNeedactionPreviewComponent/threadNeedactionPreviewView}
                        .{ThreadNeedactionPreviewView/thread}
                        .{Thread/avatarCacheKey}
                [group]
                    /web/image/mail.channel/
                    .{+}
                        @record
                        .{DiscussSidebarCategoryItem/channelId}
                    .{+}
                        /image_128
                    .{+}
                        ?unique=
                    .{+}
                        @record
                        .{ThreadNeedactionPreviewComponent/threadNeedactionPreviewView}
                        .{ThreadNeedactionPreviewView/thread}
                        .{Thread/avatarCacheKey}
                [chat]
                    {if}
                        @record
                        .{DiscussSidebarCategoryItem/channel}
                        .{Thread/correspondent}
                    {else}
                        @record
                        .{DiscussSidebarCategoryItem/channel}
                        .{Thread/correspondent}
                        .{Partner/avatarUrl}
                []
                    /mail/static/src/img/smiley/avatar.jpg
`;
