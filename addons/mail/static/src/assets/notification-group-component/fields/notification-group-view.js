/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            notificationGroupView
        [Field/model]
            NotificationGroupComponent
        [Field/type]
            one
        [Field/target]
            NotificationGroupView
        [Field/isRequired]
            true
`;
