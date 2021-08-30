/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Context
        [Context/name]
            notification
        [Context/model]
            NotificationPopoverComponent
        [Model/fields]
            notification
        [Model/template]
            notificationForeach
                notification
                    notificationIcon
                    notificationPartnerName
`;
