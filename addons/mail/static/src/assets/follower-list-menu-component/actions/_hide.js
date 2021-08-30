/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            FollowerListMenuComponent/_hide
        [Action/params]
            record
                [type]
                    FollowerListMenuComponent
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [FollowerListMenuComponent/isDropdownOpen]
                        false
`;
