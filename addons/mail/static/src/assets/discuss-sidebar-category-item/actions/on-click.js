/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            DiscussSidebarCategoryItem/onClick
        [Action/params]
            ev
                [type]
                    MouseEvent
            record
                [type]
                    DiscussSidebarCategoryItem
        [Action/behavior]
            {Thread/open}
                @record
                .{DiscussSidebarCategoryItem/channel}
`;
