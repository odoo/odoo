/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            notificationView
        [Element/model]
            NotificationListComponent:notificationView
        [Field/type]
            one
        [Field/target]
            NotificationView
        [Field/isRequired]
            true
`;
