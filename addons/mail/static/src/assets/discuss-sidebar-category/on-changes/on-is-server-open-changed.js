/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles change of open state coming from the server. Useful to
        clear pending state once server acknowledged the change.
    {onChange}
        [onChange/name]
            onIsServerOpenChanged
        [onChange/model]
            DiscussSidebarCategory
        [onChange/dependencies]
            DiscussSidebarCategory/isServerOpen
        [onChange/behavior]
            {if}
                @record
                .{DiscussSidebarCategory/isServerOpen}
                .{=}
                    @record
                    .{DiscussSidebarCategory/isPendingOpen}
            .{then}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [DiscussSidebarCategory/isPendingOpen]
                            {Record/empty}
`;
