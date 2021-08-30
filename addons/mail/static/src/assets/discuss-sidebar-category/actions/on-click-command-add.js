/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            DiscussSidebarCategory/onClickCommandAdd
        [Action/params]
            ev
                [type]
                    web.MouseEvent
            record
                [type]
                    DiscussSidebarCategory
        [Action/behavior]
            {web.Event/stopPropagation}
                @ev
            {Record/update}
                [0]
                    @record
                [1]
                    [DiscussSidebarCategory/isAddingItem]
                        true
`;
