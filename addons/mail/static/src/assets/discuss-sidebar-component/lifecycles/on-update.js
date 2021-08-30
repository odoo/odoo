/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Lifecycle
        [Lifecycle/name]
            onUpdate
        [Lifecycle/model]
            DiscussSidebarComponent
        [Lifecycle/behavior]
            {if}
                @record
                .{DiscussSidebarComponent/discussView}
                .{isFalsy}
            .{then}
                {break}
            {if}
                @record
                .{DiscussSidebarComponent/quickSearch}
            .{then}
                {Record/update}
                    [0]
                        @record
                        .{DiscussSidebarComponent/quickSearch}
                    [1]
                        [web.Element/value]
                            @record
                            .{DiscussSidebarComponent/discussView}
                            .{DiscussView/discuss}
                            .{Discuss/sidebarQuickSearchValue}
`;
