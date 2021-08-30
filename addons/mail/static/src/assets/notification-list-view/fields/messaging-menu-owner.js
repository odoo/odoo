/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            messagingMenuOwner
        [Field/model]
            NotificationListView
        [Field/type]
            one
        [Field/target]
            MessagingMenu
        [Field/isReadonly]
            true
        [Field/inverse]
            MessagingMenu/notificationListView
`;
