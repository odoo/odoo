/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine whether the messaging menu dropdown is open or not.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isOpen
        [Field/model]
            MessagingMenu
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
