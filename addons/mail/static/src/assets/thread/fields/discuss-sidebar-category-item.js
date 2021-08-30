/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the discuss sidebar category item that displays this
        thread (if any). Only applies to channels.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            discussSidebarCategoryItem
        [Field/model]
            Thread
        [Field/type]
            one
        [Field/target]
            DiscussSidebarCategoryItem
        [Field/isCausal]
            true
        [Field/isReadonly]
            true
        [Field/inverse]
            DiscussSidebarCategoryItem/channel
        [Field/compute]
            {if}
                @record
                .{Thread/model}
                .{!=}
                    mail.channel
            .{then}
                {Record/empty}
            .{elif}
                @record
                .{Thread/isPinned}
                .{isFalsy}
            .{then}
                {Record/empty}
            .{else}
                :discussSidebarCategory
                    {Thread/_getDiscussSidebarCategory}
                        @record
                {if}
                    @discussSidebarCategory
                    .{isFalsy
                .{then}
                    {Record/empty}
                {Record/insert}
                        [Record/models]
                            DiscussSidebarCategoryItem
                        [DiscussSidebarCategoryItem/category]
                            @discussSidebarCategory
`;
