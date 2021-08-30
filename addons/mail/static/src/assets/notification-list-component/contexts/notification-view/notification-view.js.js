/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Context
        [Context/name]
            notificationView
        [Model/name]
            NotificationListComponent
        [Model/fields]
            notificationView
        [Model/template]
            groupForeach
                threadPreview
                threadNeedactionPreview
                group
                notificationRequest
                separator
`;
