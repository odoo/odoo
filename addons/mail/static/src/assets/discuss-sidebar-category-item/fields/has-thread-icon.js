/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Boolean determines whether ThreadIcon will be displayed in UI.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasThreadIcon
        [Field/model]
            DiscussSidebarCategoryItem
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            {switch}
                @record
                .{DiscussSidebarCategoryItem/channelType}
            .{case}
                [channel]
                    {Record/insert}
                        [Record/models]
                            Collection
                        private
                        public
                    .{Collection/includes}
                        @record
                        .{DiscussSidebarCategoryItem/channel}
                        .{Thread/public}
                [chat]
                    true
                [group]
                    false
`;
