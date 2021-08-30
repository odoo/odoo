/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            messagingMenu
        [Field/model]
            MessagingMenuComponent
        [Field/type]
            one
        [Field/target]
            MessagingMenu
        [Field/isRequired]
            true
`;
