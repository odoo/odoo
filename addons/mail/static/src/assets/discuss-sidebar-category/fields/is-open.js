/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Boolean that determines whether this category is open.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isOpen
        [Field/model]
            DiscussSidebarCategory
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            {if}
                @record
                .{DiscussSidebarCategory/isPendingOpen}
                .{!=}
                    undefined
            .{then}
                @record
                .{DiscussSidebarCategory/isPendingOpen}
            .{else}
                @record
                .{DiscussSidebarCategory/isServerOpen}
`;
