/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            notificationGroup
        [Field/model]
            NotificationGroupView
        [Field/type]
            one
        [Field/target]
            NotificationGroup
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
        [Field/inverse]
            NotificationGroup/notificationGroupViews
`;
