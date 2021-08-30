/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Discuss/onInputQuickSearch
        [Action/params]
            discuss
                [type]
                    Discuss
            value
                [type]
                    String
        [Action/behavior]
            {Dev/comment}
                Opens all categories only when user starts to search from
                empty search value.
            {if}
                @discuss
                .{Discuss/sidebarQuickSearchValue}
                .{isFalsy}
            .{then}
                {DiscussSidebarCategory/open}
                    @discuss
                    .{Discuss/categoryChat}
                {DiscussSidebarCategory/open}
                    @discuss
                    .{Discuss/categoryChannel}
            {Record/update}
                [0]
                    @discuss
                [1]
                    [Discuss/sidebarQuickSearchValue]
                        @value
`;
