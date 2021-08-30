/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Changes the category open states when clicked.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            DiscussSidebarCategory/onHideAddingItem
        [Action/params]
            record
                [type]
                    DiscussSidebarCategory
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [DiscussSidebarCategory/isAddingItem]
                        false
`;
