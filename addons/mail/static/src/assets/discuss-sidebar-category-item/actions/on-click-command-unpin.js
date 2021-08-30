/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            DiscussSidebarCategoryItem/onClickCommandUnpin
        [Action/params]
            ev
                [type]
                    web.MouseEvent
            record
                [type]
                    DiscussSidebarCategoryItem
        [Action/behavior]
            {web.Event/stopPropagation}
                @ev
            {Thread/unsubscribe}
                @record
                .{DiscussSidebarCategoryItem/channel}
`;
