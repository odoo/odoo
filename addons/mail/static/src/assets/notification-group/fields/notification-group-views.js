/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            notificationGroupViews
        [Field/model]
            NotificationGroup
        [Field/type]
            many
        [Field/target]
            NotificationGroupView
        [Field/isCausal]
            true
        [Field/inverse]
            NotificationGroupView/notificationGroup
`;
