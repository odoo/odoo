/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            notificationListView
        [Field/model]
            NotificationListComponent
        [Field/type]
            one
        [Field/target]
            NotificationListView
        [Field/isRequired]
            true
        [Field/inverse]
            NotificationListView/notificationListComponents
`;
