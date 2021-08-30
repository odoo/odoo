/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine whether the dropdown is open or not.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isDropdownOpen
        [Field/model]
            FollowerListMenuComponent
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
