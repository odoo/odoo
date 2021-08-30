/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Changes the category open states when clicked.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            DiscussSidebarCategory/onClick
        [Action/params]
            record
                [type]
                    DiscussSidebarCategory
        [Action/behavior]
            {if}
                @record
                .DiscussSidebarCategory/{isOpen}
            .{then}
                {DiscussSidebarCategory/close}
                    @record
            .{else}
                {DiscussSidebarCategory/open}
                    @record
`;
