/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Boolean determines whether the item is currently active in discuss.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isActive
        [Field/model]
            DiscussSidebarCategoryItem
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{DiscussSidebarCategoryItem/channel}
            .{=}
                {Discuss/thread}
`;
