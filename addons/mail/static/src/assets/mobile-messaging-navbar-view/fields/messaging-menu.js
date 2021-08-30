/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            messagingMenu
        [Field/model]
            MobileMessagingNavbarView
        [Field/type]
            one
        [Field/target]
            MessagingMenu
        [Field/isReadonly]
            true
        [Field/inverse]
            MessagingMenu/mobileMessagingNavbarView
`;
