/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine whether the mobile new message input is visible or not.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isMobileNewMessageToggled
        [Field/model]
            MessagingMenu
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
